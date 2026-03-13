<template>
  <div id="app">
    <el-menu
      :default-active="activeIndex"
      class="el-menu-demo"
      mode="horizontal"
      :router="!isAdmin"
      background-color="#304156"
      text-color="#bfcbd9"
      active-text-color="#409EFF"
      :ellipsis="false"
    >
      <template v-if="isAdmin">
        <div class="logo-title" style="color: #F56C6C;">⚙️ 系统管理员后台</div>
      </template>

      <template v-else>
        <div class="logo-title">📚 智能图书推荐系统</div>
        <el-menu-item index="/">🏠 图书大厅</el-menu-item>
        <el-menu-item index="/recommend">🎯 专属推荐</el-menu-item>
        <el-menu-item index="/rated" v-if="isLoggedIn">📖 已读书籍</el-menu-item>
      </template>
      <div style="flex-grow: 1;"></div>

      <div class="auth-section">
        <template v-if="!isLoggedIn">
          <el-button type="primary" @click="openAuthDialog('login')" round>登录系统</el-button>
          <el-button @click="openAuthDialog('register')" round>注册</el-button>
        </template>

        <template v-else>
          <span class="welcome-text">欢迎，{{ username }}</span>
          <el-button type="danger" size="small" @click="logout" plain round>退出</el-button>
        </template>
      </div>
    </el-menu>

    <div :class="isAdmin ? 'admin-wrapper' : 'main-content'">
      <router-view />
    </div>

    <el-dialog v-model="authDialogVisible" :title="isLoginMode ? '用户登录' : '新用户注册'" width="400px" align-center>
      <el-form :model="authForm" label-width="60px" @submit.prevent>
        <el-form-item label="账号">
          <el-input v-model="authForm.username" placeholder="请输入账号" clearable />
        </el-form-item>
        <el-form-item label="密码">
          <el-input v-model="authForm.password" type="password" placeholder="请输入密码" show-password @keyup.enter="submitAuth" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button type="text" @click="isLoginMode = !isLoginMode" style="float: left;">
            {{ isLoginMode ? '没有账号？去注册' : '已有账号？去登录' }}
          </el-button>
          <el-button @click="authDialogVisible = false">取消</el-button>
          <el-button type="primary" @click="submitAuth" :loading="loading">
            {{ isLoginMode ? '立即登录' : '立即注册' }}
          </el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, provide, computed } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()

const isLoggedIn = ref(false)
const username = ref('')
const isAdmin = ref(false)
const loading = ref(false)
const authDialogVisible = ref(false)
const isLoginMode = ref(true)
const authForm = ref({ username: '', password: '' })
const activeIndex = computed(() => route.path)

onMounted(() => {
  const storedUserId = localStorage.getItem('user_id')
  if (storedUserId) {
    isLoggedIn.value = true
    username.value = localStorage.getItem('username') || ''
    isAdmin.value = localStorage.getItem('is_admin') === 'true'
  }
})

const openAuthDialog = (mode = 'login') => {
  isLoginMode.value = mode === 'login'
  authForm.value = { username: '', password: '' }
  authDialogVisible.value = true
}
provide('openAuthDialog', openAuthDialog)

const submitAuth = async () => {
  if (!authForm.value.username || !authForm.value.password) return ElMessage.warning('账号和密码不能为空')
  loading.value = true
  const url = isLoginMode.value ? 'http://127.0.0.1:8000/api/login/' : 'http://127.0.0.1:8000/api/register/'

  try {
    const response = await axios.post(url, authForm.value)
    if (isLoginMode.value) {
      const data = response.data
      localStorage.setItem('user_id', data.user_id)
      localStorage.setItem('username', data.username)
      localStorage.setItem('is_admin', data.is_admin)

      isLoggedIn.value = true
      username.value = data.username
      isAdmin.value = data.is_admin
      authDialogVisible.value = false
      ElMessage.success('登录成功！')

      if (data.is_admin) {
        router.push('/admin')
      } else {
        window.location.reload()
      }
    } else {
      ElMessage.success('注册成功，请直接登录！')
      isLoginMode.value = true
    }
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '请求失败，请检查账号密码')
  } finally {
    loading.value = false
  }
}

const logout = () => {
  localStorage.clear()
  isLoggedIn.value = false
  username.value = ''
  isAdmin.value = false
  ElMessage.success('已安全退出')
  router.push('/').then(() => {
    window.location.reload()
  })
}
</script>

<style>
body {
  margin: 0;
  font-family: "Helvetica Neue", Helvetica, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "微软雅黑", Arial, sans-serif;
  background-color: #f5f7fa;
}

#app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

.el-menu-demo { display: flex; align-items: center; }

.logo-title {
  font-size: 20px;
  font-weight: bold;
  color: #fff;
  margin: 0 40px 0 20px;
  letter-spacing: 1px;
  white-space: nowrap;
}

.auth-section { display: flex; align-items: center; padding-right: 20px; white-space: nowrap; }
.welcome-text { color: #fff; margin-right: 15px; font-size: 14px; }

/* 普通用户的容器样式 */
.main-content {
  flex: 1;
  padding: 30px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
  box-sizing: border-box;
}

/* 管理员的容器样式 (取消边距限制，适应全屏 Sidebar 布局) */
.admin-wrapper {
  flex: 1;
  display: flex;
  width: 100%;
  height: calc(100vh - 60px); /* 减去顶部导航的高度 */
}

.dialog-footer { width: 100%; }
</style>