<template>
  <el-container class="admin-full-layout" v-if="isAdmin">
    <el-aside width="220px" class="admin-sidebar">
      <el-menu
        :default-active="activeTab"
        class="admin-side-menu"
        @select="handleMenuSelect"
      >
        <el-menu-item index="books" class="menu-item-large">
          <span style="font-weight: bold;">📚 图书管理</span>
        </el-menu-item>
        <el-menu-item index="users" class="menu-item-large">
          <span style="font-weight: bold;">👥 用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-main class="admin-main">
      <div class="content-wrapper">

        <div v-show="activeTab === 'books'">
          <div class="panel-header"><h2>📚 图书管理面板</h2></div>

          <div class="action-card">
            <h3>➕ 新增图书</h3>
            <el-form :inline="true" :model="newBook" class="demo-form-inline">
              <el-form-item label="ISBN"><el-input v-model="newBook.isbn" placeholder="如: 978-7-111" /></el-form-item>
              <el-form-item label="书名"><el-input v-model="newBook.title" placeholder="输入书名" /></el-form-item>
              <el-form-item label="作者"><el-input v-model="newBook.author" placeholder="输入作者" /></el-form-item>
              <el-form-item label="年份"><el-input v-model="newBook.year" placeholder="如: 2024" type="number" /></el-form-item>
              <el-form-item label="出版社"><el-input v-model="newBook.publisher" placeholder="输入出版社" /></el-form-item>
              <el-form-item>
                <el-button type="primary" @click="addBook" :loading="loading">确认添加</el-button>
              </el-form-item>
            </el-form>
          </div>

          <div class="action-card">
            <h3>🔍 搜索与管理图书</h3>

            <div style="margin-bottom: 15px; max-width: 650px;">
              <el-input
                v-model="searchKeyword"
                placeholder="请输入关键字..."
                clearable
                @keyup.enter="searchBooks"
                @clear="searchBooks"
              >
                <template #prepend>
                  <el-select v-model="searchType" style="width: 100px;">
                    <el-option label="全部" value="all" />
                    <el-option label="ISBN" value="isbn" />
                    <el-option label="书名" value="title" />
                    <el-option label="作者" value="author" />
                  </el-select>
                </template>
                <template #append>
                  <el-button @click="searchBooks">搜索</el-button>
                </template>
              </el-input>
            </div>

            <el-table :data="bookList" v-loading="loadingBooks" border stripe style="width: 100%" empty-text="暂无匹配图书">
              <el-table-column prop="isbn" label="ISBN" width="130" align="center" />
              <el-table-column prop="title" label="书名" min-width="180" show-overflow-tooltip />
              <el-table-column prop="author" label="作者" width="150" show-overflow-tooltip />
              <el-table-column prop="publisher" label="出版社" width="150" show-overflow-tooltip />
              <el-table-column label="综合评分" width="100" align="center">
                <template #default="scope">
                  <span style="color: #ff9900; font-weight: bold;">
                    {{ scope.row.avg_rating > 0 ? scope.row.avg_rating.toFixed(1) : '暂无' }}
                  </span>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="120" align="center">
                <template #default="scope">
                  <el-button type="danger" size="small" @click="handleDeleteBook(scope.row)" plain>删除</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </div>

        <div v-show="activeTab === 'users'">
          <div class="panel-header"><h2>👥 用户管理面板</h2></div>

          <div class="action-card">
            <h3>👤 用户列表</h3>
            <el-table :data="userList" v-loading="loadingUsers" border stripe style="width: 100%; margin-top: 15px;" empty-text="暂无用户">
              <el-table-column prop="user_id" label="用户 ID" width="120" align="center" />
              <el-table-column prop="username" label="用户名" />
              <el-table-column label="身份角色" width="150" align="center">
                <template #default="scope">
                  <el-tag :type="scope.row.is_admin ? 'danger' : 'success'">
                    {{ scope.row.is_admin ? '管理员' : '普通读者' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="危险操作" width="150" align="center">
                <template #default="scope">
                  <el-button type="danger" size="small" @click="handleDeleteUser(scope.row)" plain>销毁用户</el-button>
                </template>
              </el-table-column>
            </el-table>

            <div style="margin-top: 15px; text-align: right;">
              <el-button @click="fetchUsers" size="small" icon="el-icon-refresh">刷新列表</el-button>
            </div>
          </div>
        </div>

      </div>
    </el-main>
  </el-container>

  <div v-else style="padding: 50px; text-align: center;">
    <el-alert title="权限拒绝" type="error" description="您没有管理员权限，无法访问此页面。" show-icon />
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

const isAdmin = ref(false)
const operatorId = ref(null)
const loading = ref(false)
const activeTab = ref('books')

// ===== 图书管理状态 =====
const newBook = ref({ isbn: '', title: '', author: '', year: '', publisher: '' })
const searchKeyword = ref('')
const searchType = ref('all')
const bookList = ref([])
const loadingBooks = ref(false)

// ===== 用户管理状态 =====
const userList = ref([])
const loadingUsers = ref(false)

const API_BASE = 'http://127.0.0.1:8000/api'

onMounted(() => {
  operatorId.value = localStorage.getItem('user_id')
  isAdmin.value = localStorage.getItem('is_admin') === 'true'

  if (isAdmin.value) {
    searchBooks()
  }
})

const handleMenuSelect = (index) => {
  activeTab.value = index
  if (index === 'users') fetchUsers()
  if (index === 'books' && bookList.value.length === 0) searchBooks()
}

// === 图书相关逻辑 ===
const searchBooks = async () => {
  loadingBooks.value = true
  try {
    // 核心修改：请求时带上 search_type 和 scope=admin
    const res = await axios.get(`${API_BASE}/books/?search=${searchKeyword.value}&search_type=${searchType.value}&scope=admin`)
    bookList.value = res.data.results || []
  } catch (error) {
    ElMessage.error('获取图书列表失败')
  } finally {
    loadingBooks.value = false
  }
}

const addBook = async () => {
  if (!newBook.value.isbn || !newBook.value.title) return ElMessage.warning('ISBN 和书名不能为空')
  loading.value = true
  try {
    const payload = {
      isbn: newBook.value.isbn,
      title: newBook.value.title,
      operator_id: operatorId.value
    }
    if (newBook.value.author) payload.author = newBook.value.author
    if (newBook.value.year) payload.year = parseInt(newBook.value.year)
    if (newBook.value.publisher) payload.publisher = newBook.value.publisher

    const res = await axios.post(`${API_BASE}/admin/books/`, payload)
    ElMessage.success(res.data.message || '添加成功')
    newBook.value = { isbn: '', title: '', author: '', year: '', publisher: '' }
    searchBooks()
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '添加失败')
  } finally {
    loading.value = false
  }
}

const handleDeleteBook = (row) => {
  ElMessageBox.confirm(`确定要彻底删除图书《${row.title}》(ISBN: ${row.isbn}) 吗？`, '删除警告', {
    confirmButtonText: '确定删除', cancelButtonText: '取消', type: 'warning'
  }).then(async () => {
    loadingBooks.value = true
    try {
      const res = await axios.delete(`${API_BASE}/admin/books/?isbn=${row.isbn}&operator_id=${operatorId.value}`)
      ElMessage.success(res.data.message)
      searchBooks()
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '删除失败')
    } finally {
      loadingBooks.value = false
    }
  }).catch(() => {})
}

// === 用户相关逻辑 ===
const fetchUsers = async () => {
  loadingUsers.value = true
  try {
    const res = await axios.get(`${API_BASE}/admin/users/?operator_id=${operatorId.value}`)
    userList.value = res.data.data
  } catch (error) {
    ElMessage.error('获取用户列表失败')
  } finally {
    loadingUsers.value = false
  }
}

const handleDeleteUser = (row) => {
  ElMessageBox.confirm(
    `极度危险！确定要销毁用户 "${row.username}" (ID: ${row.user_id}) 及其所有评价数据吗？`,
    '核弹级警告',
    { confirmButtonText: '我确定，直接销毁', cancelButtonText: '手滑了', type: 'error' }
  ).then(async () => {
    try {
      const res = await axios.delete(`${API_BASE}/admin/users/?user_id=${row.user_id}&operator_id=${operatorId.value}`)
      ElMessage.success(res.data.message)
      fetchUsers()
    } catch (error) {
      ElMessage.error(error.response?.data?.error || '删除失败')
    }
  }).catch(() => {})
}
</script>

<style scoped>
.admin-full-layout { height: 100%; width: 100%; }
.admin-sidebar { background-color: #fff; border-right: 1px solid #e6e6e6; box-shadow: 2px 0 6px rgba(0,21,41,.05); }
.admin-side-menu { border-right: none; height: 100%; }
.menu-item-large { font-size: 16px; height: 60px; line-height: 60px; }
.admin-main { background-color: #f5f7fa; padding: 20px; overflow-y: auto; }
.content-wrapper { max-width: 1200px; margin: 0 auto; }
.panel-header { margin-bottom: 20px; color: #333; }
.action-card { padding: 20px; margin-bottom: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 1px 4px rgba(0,21,41,.08); }
</style>