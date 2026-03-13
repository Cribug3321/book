<template>
  <div class="home">
    <div class="header-container">
      <h2>全部图书大厅</h2>
      <div class="search-box">
        <el-input
            v-model="searchKeyword"
            placeholder="输入书名或作者搜索..."
            clearable
            @clear="handleSearch"
            @keyup.enter="handleSearch"
            style="width: 300px; margin-right: 10px;"
        >
          <template #prefix>🔍</template>
        </el-input>
        <el-button type="primary" @click="handleSearch">搜索</el-button>
      </div>
    </div>
    <el-empty v-if="!loading && books.length === 0" description="没有找到相关的书籍，换个词试试吧~"/>

    <el-row :gutter="20" v-loading="loading" v-else>
      <el-col :span="6" v-for="book in books" :key="book.isbn" style="margin-bottom: 20px;">
        <el-card shadow="hover" class="book-card">
          <div class="book-info">
            <h4 class="title" :title="book.title">{{ book.title }}</h4>
            <p class="rating-text">
              ⭐ 综合评分:
              <span v-if="book.avg_rating" style="color: #ff9900; font-weight: bold;">
                {{ book.avg_rating.toFixed(1) }} 分
              </span>
              <span v-else style="color: #ccc;">暂无评分</span>
            </p>
            <p class="author">作者: {{ book.author }}</p>
            <p class="year">年份: {{ book.year }}</p>
            <p class="publisher">出版社: {{ book.publisher }}</p>
            <p class="isbn">ISBN: {{ book.isbn }}</p>
          </div>

          <div class="rating-section" @click.capture="checkLoginBeforeRate" :class="{'has-rated': book.user_rating}">
            <span v-if="book.user_rating"
                  style="font-size: 13px; color: #409EFF; margin-right: 10px; font-weight: bold;">我的评分:</span>
            <span v-else style="font-size: 13px; color: #999; margin-right: 10px;">我来打分:</span>

            <el-rate
                v-model="book.tempStar"
                :max="5"
                allow-half
                @change="(val) => submitRating(book, val)"
            />
          </div>
        </el-card>
      </el-col>
    </el-row>

    <div class="pagination-container" v-if="totalBooks > 0">
      <el-pagination
          background
          layout="prev, pager, next"
          :total="totalBooks"
          :page-size="20"
          :current-page="currentPage"
          @current-change="handlePageChange"
      />
    </div>
  </div>
</template>

<script setup>
import {ref, onMounted, inject} from 'vue'
import axios from 'axios'
import {ElMessage} from 'element-plus'

const books = ref([])
const totalBooks = ref(0)
const loading = ref(false)
const currentPage = ref(1)          // 新增：记录当前页码
const searchKeyword = ref('')       // 新增：记录搜索关键字

// 注入 App.vue 的登录弹窗方法
const openAuthDialog = inject('openAuthDialog')

// 修改点 2：在请求的 URL 中拼上 search 参数
// 修改 fetchBooks，加上 user_id 参数，并将 user_rating 换算成星星数
const fetchBooks = async (page = 1) => {
  loading.value = true
  currentPage.value = page
  const userId = localStorage.getItem('user_id') || '' // 取出当前登录的 userId
  try {
    const response = await axios.get(`http://127.0.0.1:8000/api/books/?page=${page}&search=${searchKeyword.value}&user_id=${userId}`)

    // 如果 book.user_rating 有值，就除以 2 变成星星；否则给 0
    books.value = response.data.results.map(book => ({
      ...book,
      tempStar: book.user_rating ? book.user_rating / 2 : 0
    }))
    totalBooks.value = response.data.count
  } catch (error) {
    console.error("获取图书失败:", error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchBooks(1)
})

const handlePageChange = (val) => {
  fetchBooks(val)
}

// 新增：点击搜索或按下回车时触发，重置到第一页
const handleSearch = () => {
  fetchBooks(1)
}

// ========== 新增：打分相关逻辑 ==========

// 拦截未登录用户的点击
const checkLoginBeforeRate = (event) => {
  const userId = localStorage.getItem('user_id')
  if (!userId) {
    // 阻止星星组件的默认点击行为
    event.stopPropagation()
    event.preventDefault()
    ElMessage.warning('打分前请先登录~')
    if (openAuthDialog) openAuthDialog() // 呼出登录弹窗
  }
}

// 提交分数到后端
// 修改 submitRating 的参数，直接传入 book 对象而不是 isbn，这样打分后前端状态能立马改变
const submitRating = async (book, starVal) => {
  const currentUserId = localStorage.getItem('user_id')
  if (!currentUserId) return

  const ratingScore = starVal * 2
  try {
    const response = await axios.post('http://127.0.0.1:8000/api/rate/', {
      user_id: currentUserId,
      isbn: book.isbn,
      rating: ratingScore
    })
    // 打分成功后，局部更新该书的状态
    book.user_rating = ratingScore
    ElMessage.success(response.data.message || `成功打出 ${ratingScore} 分！`)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '打分失败，请稍后重试')
  }
}
</script>

<style scoped>
/* 新增：让标题和搜索框在一行显示，并两端对齐 */
.header-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.search-box {
  display: flex;
  align-items: center;
}

.book-card {
  height: 270px; /* 从 250px 加高到 270px */
  display: flex;
  flex-direction: column;
  position: relative;
}

.rating-text {
  font-size: 13px;
  margin: 5px 0;
}

.title {
  font-size: 16px;
  margin: 0 0 10px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.author, .year, .publisher, .isbn {
  font-size: 13px;
  color: #666;
  margin: 5px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination-container {
  display: flex;
  justify-content: center;
  margin-top: 30px;
}

/* 新增：打分区域固定在卡片底部 */
.rating-section {
  position: absolute;
  bottom: 15px;
  left: 20px;
  display: flex;
  align-items: center;
}

.has-rated {
  background-color: #f0f9eb;
  padding: 5px 10px;
  border-radius: 20px;
  left: 10px !important; /* 微调一下加了内边距后的位置 */
}
</style>