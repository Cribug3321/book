<template>
  <div class="rated-books">
    <h2>📖 我的已读书籍</h2>

    <el-empty v-if="!isLoggedIn" description="请先登录查看你的阅读记录">
      <el-button type="primary" @click="promptLogin">去登录</el-button>
    </el-empty>

    <div v-else>
      <el-empty v-if="!loading && ratedBooks.length === 0" description="你还没有评价过任何书籍，快去大厅逛逛吧~" />

      <el-row :gutter="20" v-loading="loading">
        <el-col :span="6" v-for="book in ratedBooks" :key="book.isbn" style="margin-bottom: 20px;">
          <el-card shadow="hover" class="book-card">

            <div class="book-info">
              <h4 class="title" :title="book.title">{{ book.title }}</h4>
              <p class="author">作者: {{ book.author }}</p>
              <p class="year">年份: {{ book.year }}</p>
              <p class="publisher">出版社: {{ book.publisher }}</p>
              <p class="isbn">ISBN: {{ book.isbn }}</p>
            </div>

            <div class="rating-section">
              <span style="font-size: 13px; color: #409EFF; margin-right: 10px; font-weight: bold;">我的评分:</span>
              <el-rate
                v-model="book.tempStar"
                :max="5"
                allow-half
                @change="(val) => submitRating(book.isbn, val)"
              />
            </div>

          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const ratedBooks = ref([])
const loading = ref(false)
const isLoggedIn = ref(false)
const userId = ref(null)

const openAuthDialog = inject('openAuthDialog')

onMounted(() => {
  const storedUserId = localStorage.getItem('user_id')
  if (storedUserId) {
    isLoggedIn.value = true
    userId.value = storedUserId
    getRatedBooks()
  }
})

const promptLogin = () => {
  if (openAuthDialog) openAuthDialog()
}

const getRatedBooks = async () => {
  loading.value = true

  try {
    const response = await axios.get(`http://127.0.0.1:8000/api/rated/?user_id=${userId.value}`)

    if (response.data.data) {
      // 后端传过来的是 1-10 分的 user_rating，我们需要除以 2 换算成前端的 1-5 颗星星
      ratedBooks.value = response.data.data.map(book => ({
        ...book,
        tempStar: book.user_rating / 2
      }))
    }
  } catch (error) {
    console.error("获取已读记录失败:", error)
    ElMessage.error('获取记录失败，请检查后端服务。')
  } finally {
    loading.value = false
  }
}

// 提交分数到后端 (修改打分)
const submitRating = async (isbn, starVal) => {
  const currentUserId = localStorage.getItem('user_id')
  if (!currentUserId) return

  const ratingScore = starVal * 2

  try {
    const response = await axios.post('http://127.0.0.1:8000/api/rate/', {
      user_id: currentUserId,
      isbn: isbn,
      rating: ratingScore
    })
    ElMessage.success(`评分已更新为 ${ratingScore} 分！`)
  } catch (error) {
    ElMessage.error(error.response?.data?.error || '修改打分失败，请稍后重试')
  }
}
</script>

<style scoped>
.book-card {
  height: 240px;
  position: relative;
  display: flex;
  flex-direction: column;
}
.title {
  font-size: 16px; margin: 0 0 10px 0; overflow: hidden; text-overflow: ellipsis; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical;
}
.author, .year, .publisher, .isbn {
  font-size: 13px; color: #666; margin: 5px 0; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;
}
.rating-section {
  position: absolute;
  bottom: 15px;
  left: 20px;
  display: flex;
  align-items: center;
  background-color: #f0f9eb; /* 加一点浅绿色背景区分一下 */
  padding: 5px 10px;
  border-radius: 20px;
}
</style>