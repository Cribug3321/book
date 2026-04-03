import { createRouter, createWebHistory } from 'vue-router'
import Home from '../views/Home.vue'
import Recommend from '../views/Recommend.vue'
import RatedBooks from '../views/RatedBooks.vue'
import Admin from '../views/Admin.vue'

const routes = [
  { path: '/', name: 'Home', component: Home },
  { path: '/recommend', name: 'Recommend', component: Recommend },
  { path: '/rated', name: 'RatedBooks', component: RatedBooks },
  { path: '/admin', name: 'Admin', component: Admin }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// ======== 新增：全局路由守卫 ========
router.beforeEach((to, from, next) => {
  // 从本地缓存获取当前用户的权限状态
  const isAdmin = localStorage.getItem('is_admin') === 'true'

  // 逻辑 1：如果是管理员，且访问的不是 /admin 页面，强制重定向到 /admin
  if (isAdmin && to.path !== '/admin') {
    next('/admin')
  }
  // 逻辑 2：如果是普通用户（未登录或非管理员），且试图访问 /admin 页面，强制拦截回首页
  else if (!isAdmin && to.path === '/admin') {
    next('/')
  }
  // 其他正常情况，直接放行
  else {
    next()
  }
})
// ====================================

export default router