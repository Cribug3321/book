<template>
  <div class="recommend">
    <h2>🎯 专属个性化推荐</h2>

    <el-empty v-if="!isLoggedIn" description="请先登录，以便我们为你生成专属书单">
      <el-button type="primary" @click="promptLogin">去登录</el-button>
    </el-empty>

    <div v-else>
      <el-alert
        v-if="recommendStatus === 'cold_start'"
        title="全站高分榜单"
        type="warning"
        :description="statusMessage"
        show-icon
        style="margin-bottom: 20px;"
        :closable="false"
      />

      <el-alert
        v-if="recommendStatus === 'warm_start'"
        title="基于您的近期反馈"
        type="info"
        :description="statusMessage"
        show-icon
        style="margin-bottom: 20px;"
        :closable="false"
      />

      <el-row :gutter="20" v-loading="loading">
        <el-col :span="6" v-for="(book, index) in recommendedBooks" :key="book.isbn" style="margin-bottom: 20px;">
          <el-card shadow="hover" class="book-card">

            <div class="rank-badge" :style="{ backgroundColor: recommendStatus === 'cold_start' ? '#faad14' : (recommendStatus === 'warm_start' ? '#409EFF' : '#ff4d4f') }">
              Top {{ index + 1 }}
            </div>

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
              <span v-if="book.user_rating" style="font-size: 13px; color: #409EFF; margin-right: 10px; font-weight: bold;">我的评分:</span>
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
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, inject } from 'vue'
import axios from 'axios'
import { ElMessage } from 'element-plus'

const recommendedBooks = ref([])
const loading = ref(false)
const recommendStatus = ref('') // 'success', 'cold_start', 'warm_start'
const statusMessage = ref('')
const isLoggedIn = ref(false)
const userId = ref(null)

// 注入 App.vue 提供的全局登录弹窗方法
const openAuthDialog = inject('openAuthDialog')

// 页面加载时检查登录状态，如果已登录则自动请求推荐数据
onMounted(() => {
  const storedUserId = localStorage.getItem('user_id')
  if (storedUserId) {
    isLoggedIn.value = true
    userId.value = storedUserId
    getRecommendations()
  }
})

// 呼出登录框
const promptLogin = () => {
  if (openAuthDialog) {
    openAuthDialog()
  } else {
    ElMessage.warning('请点击右上角进行登录')
  }
}

// 获取推荐列表
const getRecommendations = async () => {
  loading.value = true
  recommendStatus.value = ''

  try {
    const response = await axios.get(`http://127.0.0.1:8000/api/recommend/?user_id=${userId.value}`)

    if (response.data.data && response.data.data.length > 0) {
      // 解析后端传来的 user_rating，如果是 10 分制则除以 2 映射给前端的 5 星组件
      recommendedBooks.value = response.data.data.map(book => ({
        ...book,
        tempStar: book.user_rating ? book.user_rating / 2 : 0
      }))

      recommendStatus.value = response.data.status
      statusMessage.value = response.data.message

      if (response.data.status === 'success') {
        ElMessage.success(response.data.message)
      }
    }
  } catch (error) {
    console.error("获取推荐失败:", error)
    ElMessage.error('获取推荐失败，请检查后端服务。')
  } finally {
    loading.value = false
  }
}

// 拦截未登录用户的打分操作
const checkLoginBeforeRate = (event) => {
  const currentUserId = localStorage.getItem('user_id')
  if (!currentUserId) {
    event.stopPropagation()
    event.preventDefault()
    ElMessage.warning('打分前请先登录~')
    if (openAuthDialog) openAuthDialog()
  }
}

// 提交新的打分到后端
const submitRating = async (book, starVal) => {
  const currentUserId = localStorage.getItem('user_id')
  if (!currentUserId) return

  // 将 5 星制转回 10 分制传给后端
  const ratingScore = starVal * 2

  try {
    const response = await axios.post('http://127.0.0.1:8000/api/rate/', {
      user_id: currentUserId,
      isbn: book.isbn,
      rating: ratingScore
    })

    // 更新本地卡片的状态，让它立刻变成“已评分”的样式
    book.user_rating = ratingScore
    ElMessage.success(response.data.message || `成功打出 ${ratingScore} 分！`)

  } catch (error) {
    ElMessage.error(error.response?.data?.error || '打分失败，请稍后重试')
  }
}
</script>

<style scoped>
.book-card {
  height: 270px;
  position: relative;
  display: flex;
  flex-direction: column;
}

.rank-badge {
  position: absolute;
  top: 0;
  right: 0;
  color: white;
  padding: 4px 10px;
  font-size: 12px;
  font-weight: bold;
  border-bottom-left-radius: 8px;
  transition: background-color 0.3s;
}

.title {
  font-size: 16px;
  margin: 15px 0 10px 0;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.rating-text {
  font-size: 13px;
  margin: 5px 0;
}

.author, .year, .publisher, .isbn {
  font-size: 13px;
  color: #666;
  margin: 5px 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.rating-section {
  position: absolute;
  bottom: 15px;
  left: 20px;
  display: flex;
  align-items: center;
  transition: all 0.3s;
}

/* 已评分状态的专属样式 */
.has-rated {
  background-color: #f0f9eb;
  padding: 5px 10px;
  border-radius: 20px;
  left: 10px !important;
}
</style>