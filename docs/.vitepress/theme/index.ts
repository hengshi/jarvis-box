import DefaultTheme from 'vitepress/theme'
import { h } from 'vue'
import './custom.css'

export default {
  extends: DefaultTheme,
  Layout: () => h(DefaultTheme.Layout, null, {
    'nav-bar-content-after': () => h('a', { href: '/status', target: '_self', class: 'workbench-link' }, '返回工作台'),
  }),
}
