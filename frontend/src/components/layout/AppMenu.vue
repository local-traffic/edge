<script setup>
import { ref } from 'vue';
import AppMenuItem from './AppMenuItem.vue';

const model = ref([
    {
        label: 'Home',
        items: [
            {
                label: 'Dashboard',
                icon: 'pi pi-fw pi-home',
                to: '/'
            }
        ]
    },
    {
        label: 'Pages',
        icon: 'pi pi-fw pi-briefcase',
        path: '/pages',
        items: [
            {
                label: 'Live View',
                icon: 'pi pi-fw pi-video',
                to: '/stream'
            },
            {
                label: 'Detections',
                icon: 'pi pi-fw pi-car',
                to: '/detections'
            },
            {
                label: 'Tracks analysis',
                icon: 'pi pi-fw pi-map',
                to: '/tracks'
            },
            {
                label: 'Statistics',
                icon: 'pi pi-fw pi-chart-bar',
                to: '/statistics'
            }
        ]
    },
     {
        label: 'Setting',
        icon: 'pi pi-fw pi-briefcase',
         items: [
            {
                label: 'Camera Perspective',
                icon: 'pi pi-fw pi-globe',
                to: '/calibration'
            },
            {
                label: 'Noise Measurement',
                icon: 'pi pi-fw pi-microphone',
                to: '/noise'
            }
        ]

     },
    {
        label: 'Other',
        items: [
            {
                label: 'Style guide catalog for app',
                icon: 'pi pi-fw pi-globe',
                to: '/style-guide'
            }
        
        ]
    },
  
    {
        label: 'Based on Sakai',
        items: [

            {
                label: 'Sakai live',
                icon: 'pi pi-fw pi-book',
                url: 'https://sakai.primevue.org',
                target: '_blank'
            },
            {
                label: 'Sakai github',
                icon: 'pi pi-fw pi-github',
                url: 'https://github.com/primefaces/sakai-vue',
                target: '_blank'
            }
        ]
    }
]);
</script>

<template>
    <ul class="layout-menu">
        <template v-for="(item, i) in model" :key="item">
            <app-menu-item v-if="!item.separator" :item="item" :index="i"></app-menu-item>
            <li v-if="item.separator" class="menu-separator"></li>
        </template>
    </ul>
</template>

<style lang="scss" scoped></style>
