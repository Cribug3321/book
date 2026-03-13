import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Recommend from '../views/Recommend.vue'
import RatedBooks from '../views/RatedBooks.vue'
import Admin from '../views/Admin.vue' // 引入管理员页面

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/recommend', name: 'Recommend', component: Recommend },
  { path: '/rated', name: 'RatedBooks', component: RatedBooks },
  { path: '/admin', name: 'Admin', component: Admin } // 注册路由
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router