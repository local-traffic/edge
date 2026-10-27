"""
Playwright test for SaveClipButton component.
Tests the Save Clip functionality in the Live Stream view using API mocking.
"""
from playwright.sync_api import sync_playwright, expect

BASE_URL = "http://localhost:3000"


def test_save_clip_button_with_mocked_api():
    """Test the SaveClipButton component with mocked backend API responses."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Mock the clip info API to simulate available buffer
        def handle_clip_info(route):
            route.fulfill(
                status=200,
                content_type='application/json',
                body='{"available": true, "frames": 150, "duration": 5.0, "max_duration": 5.0, "fps": 30}'
            )

        # Mock the save clip API to simulate successful save
        def handle_save_clip(route):
            route.fulfill(
                status=200,
                content_type='application/json',
                body='{"success": true, "filename": "clip_20260122_120000.avi", "frames": 150, "duration": 5.0, "fps": 30}'
            )

        # Mock video feed with empty response (just to prevent hanging requests)
        def handle_video_feed(route):
            route.abort()

        # Mock other API calls to prevent errors
        def handle_zones(route):
            route.fulfill(status=200, content_type='application/json', body='{"zones": []}')

        def handle_threshold(route):
            route.fulfill(status=200, content_type='application/json', body='{"threshold": 0.3}')

        def handle_metrics(route):
            route.fulfill(status=200, content_type='application/json', body='{"fps": 30, "inference_ms": 10}')

        def handle_camera(route):
            route.fulfill(status=200, content_type='application/json', body='{"is_picamera": false, "settings": {}}')

        def handle_config(route):
            route.fulfill(status=200, content_type='application/json', body='{"web_stream": true}')

        def handle_events(route):
            route.fulfill(status=200, content_type='application/json', body='{"events": []}')

        # Set up route handlers
        page.route('**/api/clip/info', handle_clip_info)
        page.route('**/api/clip/save', handle_save_clip)
        page.route('**/video_feed', handle_video_feed)
        page.route('**/api/zones', handle_zones)
        page.route('**/api/threshold', handle_threshold)
        page.route('**/metrics', handle_metrics)
        page.route('**/api/camera/settings', handle_camera)
        page.route('**/api/config', handle_config)
        page.route('**/api/events', handle_events)
        page.route('**/api/events/stream', lambda route: route.abort())

        # Navigate to Live Stream page
        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')

        # Take initial screenshot
        page.screenshot(path='/tmp/save_clip_initial.png', full_page=True)
        print("Initial screenshot saved to /tmp/save_clip_initial.png")

        # Find the Save Clip panel
        save_clip_panel = page.locator('text=Save Clip').first
        expect(save_clip_panel).to_be_visible()
        print("Save Clip panel found")

        # Wait for buffer info to load
        page.wait_for_timeout(1000)

        # Check for buffer info display (should show "Buffer: 5.0s / 5.0s")
        buffer_info = page.locator('text=/Buffer:.*5\\.0s/')
        expect(buffer_info).to_be_visible(timeout=5000)
        buffer_text = buffer_info.first.text_content()
        print(f"Buffer info displayed: {buffer_text}")
        assert "5.0s" in buffer_text, "Buffer info should show duration"

        # Find the Save Clip button
        save_button = page.get_by_role('button', name='Save Clip')
        expect(save_button).to_be_visible()
        expect(save_button).to_be_enabled()
        print("Save Clip button is visible and enabled")

        # Click the save button
        save_button.click()
        print("Clicked Save Clip button")

        # Wait for success message
        success_message = page.locator('text=/Saved clip_.*\\.avi/')
        expect(success_message).to_be_visible(timeout=5000)
        msg = success_message.first.text_content()
        print(f"SUCCESS: {msg}")
        assert "clip_20260122_120000.avi" in msg, "Success message should contain filename"
        assert "5.0s" in msg, "Success message should contain duration"

        # Take screenshot after successful save
        page.screenshot(path='/tmp/save_clip_success.png', full_page=True)
        print("Success screenshot saved to /tmp/save_clip_success.png")

        browser.close()
        print("Test completed successfully!")


def test_save_clip_button_buffer_unavailable():
    """Test SaveClipButton when buffer is not available."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Mock clip info API to simulate unavailable buffer
        def handle_clip_info(route):
            route.fulfill(
                status=200,
                content_type='application/json',
                body='{"available": false}'
            )

        def handle_video_feed(route):
            route.abort()

        def handle_zones(route):
            route.fulfill(status=200, content_type='application/json', body='{"zones": []}')

        def handle_threshold(route):
            route.fulfill(status=200, content_type='application/json', body='{"threshold": 0.3}')

        def handle_metrics(route):
            route.fulfill(status=200, content_type='application/json', body='{"fps": 30}')

        def handle_camera(route):
            route.fulfill(status=200, content_type='application/json', body='{"is_picamera": false, "settings": {}}')

        def handle_config(route):
            route.fulfill(status=200, content_type='application/json', body='{"web_stream": true}')

        def handle_events(route):
            route.fulfill(status=200, content_type='application/json', body='{"events": []}')

        page.route('**/api/clip/info', handle_clip_info)
        page.route('**/video_feed', handle_video_feed)
        page.route('**/api/zones', handle_zones)
        page.route('**/api/threshold', handle_threshold)
        page.route('**/metrics', handle_metrics)
        page.route('**/api/camera/settings', handle_camera)
        page.route('**/api/config', handle_config)
        page.route('**/api/events', handle_events)
        page.route('**/api/events/stream', lambda route: route.abort())

        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1000)

        # Check for "Buffer info unavailable" text
        unavailable_text = page.locator('text=Buffer info unavailable')
        expect(unavailable_text).to_be_visible(timeout=5000)
        print("Buffer unavailable message displayed")

        # Button should be disabled
        save_button = page.get_by_role('button', name='Save Clip')
        expect(save_button).to_be_disabled()
        print("Save Clip button is correctly disabled when buffer unavailable")

        page.screenshot(path='/tmp/save_clip_unavailable.png', full_page=True)
        print("Screenshot saved to /tmp/save_clip_unavailable.png")

        browser.close()
        print("Test completed successfully!")


def test_save_clip_button_error_handling():
    """Test SaveClipButton error handling when save fails."""

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        # Mock clip info API
        def handle_clip_info(route):
            route.fulfill(
                status=200,
                content_type='application/json',
                body='{"available": true, "frames": 150, "duration": 5.0, "max_duration": 5.0, "fps": 30}'
            )

        # Mock save clip API to return error
        def handle_save_clip(route):
            route.fulfill(
                status=500,
                content_type='application/json',
                body='{"error": "Failed to create video writer"}'
            )

        def handle_video_feed(route):
            route.abort()

        def handle_zones(route):
            route.fulfill(status=200, content_type='application/json', body='{"zones": []}')

        def handle_threshold(route):
            route.fulfill(status=200, content_type='application/json', body='{"threshold": 0.3}')

        def handle_metrics(route):
            route.fulfill(status=200, content_type='application/json', body='{"fps": 30}')

        def handle_camera(route):
            route.fulfill(status=200, content_type='application/json', body='{"is_picamera": false, "settings": {}}')

        def handle_config(route):
            route.fulfill(status=200, content_type='application/json', body='{"web_stream": true}')

        def handle_events(route):
            route.fulfill(status=200, content_type='application/json', body='{"events": []}')

        page.route('**/api/clip/info', handle_clip_info)
        page.route('**/api/clip/save', handle_save_clip)
        page.route('**/video_feed', handle_video_feed)
        page.route('**/api/zones', handle_zones)
        page.route('**/api/threshold', handle_threshold)
        page.route('**/metrics', handle_metrics)
        page.route('**/api/camera/settings', handle_camera)
        page.route('**/api/config', handle_config)
        page.route('**/api/events', handle_events)
        page.route('**/api/events/stream', lambda route: route.abort())

        page.goto(BASE_URL)
        page.wait_for_load_state('networkidle')
        page.wait_for_timeout(1000)

        # Click save button
        save_button = page.get_by_role('button', name='Save Clip')
        expect(save_button).to_be_enabled()
        save_button.click()
        print("Clicked Save Clip button")

        # Wait for error message
        page.wait_for_timeout(1000)
        error_message = page.locator('text=/Failed to create video writer/')
        expect(error_message).to_be_visible(timeout=5000)
        print("Error message correctly displayed")

        page.screenshot(path='/tmp/save_clip_error.png', full_page=True)
        print("Screenshot saved to /tmp/save_clip_error.png")

        browser.close()
        print("Test completed successfully!")


if __name__ == '__main__':
    print("=" * 60)
    print("Test 1: Save Clip with mocked successful API")
    print("=" * 60)
    test_save_clip_button_with_mocked_api()

    print("\n" + "=" * 60)
    print("Test 2: Save Clip when buffer unavailable")
    print("=" * 60)
    test_save_clip_button_buffer_unavailable()

    print("\n" + "=" * 60)
    print("Test 3: Save Clip error handling")
    print("=" * 60)
    test_save_clip_button_error_handling()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED!")
    print("=" * 60)
