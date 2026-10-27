import threading
import time
import queue
import psycopg2
import sqlite3
from datetime import datetime, timezone
from .event_manager import Event


SCHEMA_VERSION = 4

POSTGRES_MIGRATIONS = {
    2: [
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS event_type TEXT",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS speed_ms FLOAT",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS avg_speed_ms FLOAT",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS track_distance_m FLOAT",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS track_duration_s FLOAT",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS speed_error_pct FLOAT",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'",
    ],
    3: [
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS speed_is_valid BOOLEAN DEFAULT FALSE",
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS speed_comment TEXT DEFAULT ''",
        """UPDATE traffic_events SET
            speed_is_valid = COALESCE((metadata->>'is_valid')::boolean, FALSE),
            speed_comment = COALESCE(metadata->>'comment', '')
        WHERE metadata IS NOT NULL AND metadata != '{}'::jsonb""",
        "ALTER TABLE traffic_events DROP COLUMN IF EXISTS metadata",
    ],
    4: [
        "ALTER TABLE traffic_events ADD COLUMN IF NOT EXISTS noise_db_a FLOAT",
    ]
}

SQLITE_MIGRATIONS = {
    2: [
        "ALTER TABLE traffic_events ADD COLUMN event_type TEXT",
        "ALTER TABLE traffic_events ADD COLUMN speed_ms REAL",
        "ALTER TABLE traffic_events ADD COLUMN avg_speed_ms REAL",
        "ALTER TABLE traffic_events ADD COLUMN track_distance_m REAL",
        "ALTER TABLE traffic_events ADD COLUMN track_duration_s REAL",
        "ALTER TABLE traffic_events ADD COLUMN speed_error_pct REAL",
        "ALTER TABLE traffic_events ADD COLUMN metadata TEXT DEFAULT '{}'",
    ],
    3: [
        "ALTER TABLE traffic_events ADD COLUMN speed_is_valid INTEGER DEFAULT 0",
        "ALTER TABLE traffic_events ADD COLUMN speed_comment TEXT DEFAULT ''",
        """UPDATE traffic_events SET
            speed_is_valid = CASE WHEN json_extract(metadata, '$.is_valid') = 1 THEN 1 ELSE 0 END,
            speed_comment = COALESCE(json_extract(metadata, '$.comment'), '')
        WHERE metadata IS NOT NULL AND metadata != '{}'""",
        "ALTER TABLE traffic_events DROP COLUMN metadata",
    ],
    4: [
        "ALTER TABLE traffic_events ADD COLUMN noise_db_a REAL",
    ]
}


class PostgresHandler:
    def __init__(self, connection_string, batch_size=10, flush_interval=5.0):
        self.conn_str = connection_string
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue = queue.Queue()
        self.running = True
        
        # Initialize DB (Synchronous start to ensure connectivity check)
        self._init_db()
        
        # Start background worker
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _init_db(self):
        """Creates the table if it doesn't exist and runs migrations."""
        try:
            with psycopg2.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS traffic_events (
                            time TIMESTAMPTZ NOT NULL,
                            zone_name TEXT,
                            class_name TEXT,
                            direction TEXT,
                            tracker_id INT,
                            confidence FLOAT,
                            fingerprint TEXT
                        );
                        CREATE INDEX IF NOT EXISTS idx_traffic_time ON traffic_events (time DESC);
                        CREATE INDEX IF NOT EXISTS idx_traffic_zone ON traffic_events (zone_name);
                    """)

                    cur.execute("""
                        CREATE TABLE IF NOT EXISTS schema_version (
                            version INTEGER PRIMARY KEY,
                            applied_at TIMESTAMPTZ DEFAULT NOW()
                        )
                    """)

                    cur.execute("SELECT MAX(version) FROM schema_version")
                    result = cur.fetchone()
                    current_version = result[0] if result[0] else 1

                    for version in range(current_version + 1, SCHEMA_VERSION + 1):
                        if version in POSTGRES_MIGRATIONS:
                            for sql in POSTGRES_MIGRATIONS[version]:
                                cur.execute(sql)
                            cur.execute(
                                "INSERT INTO schema_version (version) VALUES (%s)",
                                (version,)
                            )
                            print(f"Applied PostgreSQL migration to version {version}")

                conn.commit()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"DB Init Error: {e}")
            print("Warning: Database logging might not work.")

    def handle_event(self, event: Event):
        """Non-blocking add to queue."""
        self.queue.put(event)

    def _worker_loop(self):
        buffer = []
        last_flush = time.time()

        while self.running:
            try:
                # Wait for event with timeout (to handle flush interval)
                try:
                    # Wait up to 1 second for new events
                    event = self.queue.get(timeout=1.0)
                    buffer.append(event)
                except queue.Empty:
                    pass

                # Check conditions to flush
                is_time_to_flush = (time.time() - last_flush) > self.flush_interval
                is_batch_full = len(buffer) >= self.batch_size

                if (is_time_to_flush or is_batch_full) and buffer:
                    self._flush(buffer)
                    buffer = []
                    last_flush = time.time()
                    
            except Exception as e:
                print(f"Error in DB worker loop: {e}")
                time.sleep(1)  # Prevent tight loop on error

    def _flush(self, events):
        try:
            with psycopg2.connect(self.conn_str) as conn:
                with conn.cursor() as cur:
                    values = []
                    for e in events:
                        dt = datetime.fromtimestamp(e.timestamp, tz=timezone.utc)
                        speed = e.speed_measurement
                        is_valid = speed.is_valid
                        noise_db_a = float(e.noise_level.db_a)
                        values.append((
                            dt, e.zone_name, e.class_name,
                            e.direction, e.tracker_id, e.confidence, None,
                            e.event_type,
                            speed.speed_ms if is_valid else None,
                            speed.avg_speed_ms if is_valid else None,
                            speed.track_distance_m if is_valid else None,
                            speed.track_duration_s if is_valid else None,
                            speed.speed_error_pct if is_valid else None,
                            speed.is_valid,
                            speed.comment or '',
                            noise_db_a
                        ))

                    args_str = ','.join(
                        cur.mogrify(
                            "(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)", x
                        ).decode('utf-8')
                        for x in values
                    )
                    cur.execute(
                        "INSERT INTO traffic_events "
                        "(time, zone_name, class_name, direction, tracker_id, confidence, fingerprint, "
                        "event_type, speed_ms, avg_speed_ms, track_distance_m, track_duration_s, "
                        "speed_error_pct, speed_is_valid, speed_comment, noise_db_a) "
                        "VALUES " + args_str
                    )

        except Exception as e:
            print(f"DB Flush Error: {e}")

    def get_stats(self, duration_seconds=86400, bucket_size=3600,
                  merge_directions=False, group_vehicles=False):
        """Get aggregated traffic statistics."""
        try:
            with psycopg2.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    direction_select = "''" if merge_directions else "direction"

                    if group_vehicles:
                        class_select = """
                        CASE
                            WHEN class_name = 'person' THEN 'person'
                            ELSE 'Vehicles'
                        END
                        """
                        class_group_by = "CASE WHEN class_name = 'person' THEN 'person' ELSE 'Vehicles' END"
                    else:
                        class_select = "class_name"
                        class_group_by = "class_name"

                    group_by_cols = ["bucket_ts", "zone_name"]
                    if not merge_directions:
                        group_by_cols.append("direction")
                    group_by_cols.append(class_group_by)
                    group_by = ", ".join(group_by_cols)

                    start_time = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds)

                    query = f"""
                        SELECT
                            (FLOOR(EXTRACT(EPOCH FROM time) / %s) * %s)::bigint as bucket_ts,
                            zone_name,
                            {direction_select} as direction,
                            {class_select} as class_name,
                            COUNT(*) as count
                        FROM traffic_events
                        WHERE time > %s
                        GROUP BY {group_by}
                        ORDER BY bucket_ts ASC
                    """

                    cursor.execute(query, (bucket_size, bucket_size, start_time))
                    columns = ['bucket_ts', 'zone_name', 'direction', 'class_name', 'count']
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Stats Query Error: {e}")
            return []

    def get_speed_histogram(self, duration_seconds=86400, bin_size_kmh=5,
                            merge_directions=False, group_vehicles=False):
        """Get speed distribution as histogram bins."""
        try:
            with psycopg2.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    direction_select = "''" if merge_directions else "direction"

                    if group_vehicles:
                        class_select = """
                        CASE
                            WHEN class_name = 'person' THEN 'person'
                            ELSE 'Vehicles'
                        END
                        """
                        class_group_by = "CASE WHEN class_name = 'person' THEN 'person' ELSE 'Vehicles' END"
                    else:
                        class_select = "class_name"
                        class_group_by = "class_name"

                    group_by_cols = ["speed_bin", "zone_name"]
                    if not merge_directions:
                        group_by_cols.append("direction")
                    group_by_cols.append(class_group_by)
                    group_by = ", ".join(group_by_cols)

                    start_time = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds)

                    query = f"""
                        SELECT
                            (FLOOR(avg_speed_ms * 3.6 / %s) * %s)::int as speed_bin,
                            zone_name,
                            {direction_select} as direction,
                            {class_select} as class_name,
                            COUNT(*) as count
                        FROM traffic_events
                        WHERE time > %s AND speed_is_valid = TRUE AND avg_speed_ms IS NOT NULL
                        GROUP BY {group_by}
                        ORDER BY speed_bin ASC
                    """

                    cursor.execute(query, (bin_size_kmh, bin_size_kmh, start_time))
                    columns = ['speed_bin', 'zone_name', 'direction', 'class_name', 'count']
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Speed Histogram Query Error: {e}")
            return []

    def get_noise_histogram(self, duration_seconds=86400, bin_size_db=5,
                            merge_directions=False, group_vehicles=False):
        try:
            with psycopg2.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    direction_select = "''" if merge_directions else "direction"

                    if group_vehicles:
                        class_select = """
                        CASE
                            WHEN class_name = 'person' THEN 'person'
                            ELSE 'Vehicles'
                        END
                        """
                        class_group_by = "CASE WHEN class_name = 'person' THEN 'person' ELSE 'Vehicles' END"
                    else:
                        class_select = "class_name"
                        class_group_by = "class_name"

                    group_by_cols = ["noise_bin", "zone_name"]
                    if not merge_directions:
                        group_by_cols.append("direction")
                    group_by_cols.append(class_group_by)
                    group_by = ", ".join(group_by_cols)

                    start_time = datetime.now(timezone.utc) - timedelta(seconds=duration_seconds)

                    query = f"""
                        SELECT
                            (FLOOR(noise_db_a / %s) * %s)::int as noise_bin,
                            zone_name,
                            {direction_select} as direction,
                            {class_select} as class_name,
                            COUNT(*) as count
                        FROM traffic_events
                        WHERE time > %s AND noise_db_a IS NOT NULL AND noise_db_a > 0
                        GROUP BY {group_by}
                        ORDER BY noise_bin ASC
                    """

                    cursor.execute(query, (bin_size_db, bin_size_db, start_time))
                    columns = ['noise_bin', 'zone_name', 'direction', 'class_name', 'count']
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            print(f"Noise Histogram Query Error: {e}")
            return []

    def stop(self):
        self.running = False
        self.worker_thread.join()


class SQLiteHandler:
    def __init__(self, db_path="traffic_stats.db", batch_size=10, flush_interval=5.0):
        self.db_path = db_path
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self.queue = queue.Queue()
        self.running = True
        
        self._init_db()
        
        self.worker_thread = threading.Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()

    def _init_db(self):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS traffic_events (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        time REAL,
                        zone_name TEXT,
                        class_name TEXT,
                        direction TEXT,
                        tracker_id INTEGER,
                        confidence REAL
                    )
                """)
                cursor.execute("CREATE INDEX IF NOT EXISTS idx_time ON traffic_events (time)")

                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_version (
                        version INTEGER PRIMARY KEY,
                        applied_at REAL
                    )
                """)

                cursor.execute("SELECT MAX(version) FROM schema_version")
                result = cursor.fetchone()
                current_version = result[0] if result[0] else 1

                for version in range(current_version + 1, SCHEMA_VERSION + 1):
                    if version in SQLITE_MIGRATIONS:
                        for sql in SQLITE_MIGRATIONS[version]:
                            try:
                                cursor.execute(sql)
                            except sqlite3.OperationalError as e:
                                if "duplicate column" not in str(e).lower():
                                    raise
                        cursor.execute(
                            "INSERT INTO schema_version (version, applied_at) VALUES (?, ?)",
                            (version, time.time())
                        )
                        print(f"Applied SQLite migration to version {version}")

                conn.commit()
            print(f"SQLite DB initialized at {self.db_path}")
        except Exception as e:
            print(f"SQLite Init Error: {e}")

    def handle_event(self, event: Event):
        self.queue.put(event)

    def _worker_loop(self):
        buffer = []
        last_flush = time.time()
        while self.running:
            try:
                try:
                    event = self.queue.get(timeout=1.0)
                    buffer.append(event)
                except queue.Empty:
                    pass
                
                if (time.time() - last_flush > self.flush_interval or len(buffer) >= self.batch_size) and buffer:
                    self._flush(buffer)
                    buffer = []
                    last_flush = time.time()
            except Exception as e:
                print(f"SQLite Worker Error: {e}")
                time.sleep(1)

    def _flush(self, events):
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                data = []
                for e in events:
                    speed = e.speed_measurement
                    is_valid = speed.is_valid
                    noise_db_a = float(e.noise_level.db_a)
                    data.append((
                        e.timestamp, e.zone_name, e.class_name,
                        e.direction, e.tracker_id, e.confidence,
                        e.event_type,
                        speed.speed_ms if is_valid else None,
                        speed.avg_speed_ms if is_valid else None,
                        speed.track_distance_m if is_valid else None,
                        speed.track_duration_s if is_valid else None,
                        speed.speed_error_pct if is_valid else None,
                        1 if speed.is_valid else 0,
                        speed.comment or '',
                        noise_db_a
                    ))
                cursor.executemany("""
                    INSERT INTO traffic_events
                    (time, zone_name, class_name, direction, tracker_id, confidence,
                     event_type, speed_ms, avg_speed_ms, track_distance_m,
                     track_duration_s, speed_error_pct, speed_is_valid, speed_comment,
                     noise_db_a)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, data)
                conn.commit()
        except Exception as e:
            print(f"SQLite Flush Error: {e}")

    def get_stats(self, duration_seconds=86400, bucket_size=3600,
                  merge_directions=False, group_vehicles=False):
        """
        Get aggregated traffic statistics.

        Args:
            duration_seconds: Time window to query (default 24 hours)
            bucket_size: Time bucket size in seconds (default 1 hour)
            merge_directions: If True, combine in/out directions
            group_vehicles: If True, group all non-person classes as "Vehicles"
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                # Build direction selection
                if merge_directions:
                    direction_select = "'' as direction"
                else:
                    direction_select = "direction"

                # Build class_name selection
                if group_vehicles:
                    class_select = """
                    CASE
                        WHEN class_name = 'person' THEN 'person'
                        ELSE 'Vehicles'
                    END as class_name
                """
                    class_group_by = "CASE WHEN class_name = 'person' THEN 'person' ELSE 'Vehicles' END"
                else:
                    class_select = "class_name"
                    class_group_by = "class_name"

                # Build GROUP BY clause
                group_by_cols = ["bucket_ts", "zone_name"]
                if not merge_directions:
                    group_by_cols.append("direction")
                group_by_cols.append(class_group_by)
                group_by = ", ".join(group_by_cols)

                query = f"""
                    SELECT
                        (CAST(time / ? AS INTEGER) * ?) as bucket_ts,
                        zone_name,
                        {direction_select},
                        {class_select},
                        COUNT(*) as count
                    FROM traffic_events
                    WHERE time > ?
                    GROUP BY {group_by}
                    ORDER BY bucket_ts ASC
                """

                start_time = time.time() - duration_seconds
                cursor.execute(query, (bucket_size, bucket_size, start_time))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Stats Query Error: {e}")
            return []

    def get_speed_histogram(self, duration_seconds=86400, bin_size_kmh=5,
                            merge_directions=False, group_vehicles=False):
        """
        Get speed distribution as histogram bins.
        Reuses same filtering options as get_stats().
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                direction_select = "'' as direction" if merge_directions else "direction"

                if group_vehicles:
                    class_select = """
                    CASE
                        WHEN class_name = 'person' THEN 'person'
                        ELSE 'Vehicles'
                    END as class_name
                    """
                    class_group_by = "CASE WHEN class_name = 'person' THEN 'person' ELSE 'Vehicles' END"
                else:
                    class_select = "class_name"
                    class_group_by = "class_name"

                group_by_cols = ["speed_bin", "zone_name"]
                if not merge_directions:
                    group_by_cols.append("direction")
                group_by_cols.append(class_group_by)
                group_by = ", ".join(group_by_cols)

                query = f"""
                    SELECT
                        (CAST(avg_speed_ms * 3.6 / ? AS INTEGER) * ?) as speed_bin,
                        zone_name,
                        {direction_select},
                        {class_select},
                        COUNT(*) as count
                    FROM traffic_events
                    WHERE time > ? AND speed_is_valid = 1 AND avg_speed_ms IS NOT NULL
                    GROUP BY {group_by}
                    ORDER BY speed_bin ASC
                """

                start_time = time.time() - duration_seconds
                cursor.execute(query, (bin_size_kmh, bin_size_kmh, start_time))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Speed Histogram Query Error: {e}")
            return []

    def get_noise_histogram(self, duration_seconds=86400, bin_size_db=5,
                            merge_directions=False, group_vehicles=False):
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                direction_select = "'' as direction" if merge_directions else "direction"

                if group_vehicles:
                    class_select = """
                    CASE
                        WHEN class_name = 'person' THEN 'person'
                        ELSE 'Vehicles'
                    END as class_name
                    """
                    class_group_by = "CASE WHEN class_name = 'person' THEN 'person' ELSE 'Vehicles' END"
                else:
                    class_select = "class_name"
                    class_group_by = "class_name"

                group_by_cols = ["noise_bin", "zone_name"]
                if not merge_directions:
                    group_by_cols.append("direction")
                group_by_cols.append(class_group_by)
                group_by = ", ".join(group_by_cols)

                query = f"""
                    SELECT
                        (CAST(noise_db_a / ? AS INTEGER) * ?) as noise_bin,
                        zone_name,
                        {direction_select},
                        {class_select},
                        COUNT(*) as count
                    FROM traffic_events
                    WHERE time > ? AND noise_db_a IS NOT NULL AND noise_db_a > 0
                    GROUP BY {group_by}
                    ORDER BY noise_bin ASC
                """

                start_time = time.time() - duration_seconds
                cursor.execute(query, (bin_size_db, bin_size_db, start_time))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
        except Exception as e:
            print(f"Noise Histogram Query Error: {e}")
            return []

    def stop(self):
        self.running = False
        self.worker_thread.join()
