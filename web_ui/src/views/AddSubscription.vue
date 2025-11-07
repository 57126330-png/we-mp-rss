<template>
  <div class="add-subscription">
    <a-page-header
      title="添加订阅"
      subtitle="添加新的公众号订阅"
      :show-back="true"
      @back="goBack"
    />
    
    <a-card>
      <a-space direction="vertical" size="large">
        <a-space>
          <a-link @click="openDialog()">通过公众号码文章获取</a-link>
        </a-space>
      </a-space>

 <div v-if="modalVisible">
    <a-input
      v-model="articleLink"
      placeholder="请输入一个公众号文章链接地址"
      style="width: 300px; margin-bottom: 10px;"
    />
    <a-button @click="handleGetMpInfo" :loading="isFetching">获取</a-button>
  </div>


      <a-form
        ref="formRef"
        :model="form"
        :rules="rules"
        layout="vertical"
        @submit="handleSubmit"
      >
        <a-form-item label="公众号名称" field="name">
          <a-space>
            <a-select
              v-model="form.name"
              placeholder="请输入公众号名称"
              allow-clear
              allow-search
              @search="handleSearch"
            >
            <a-option v-for="item of searchResults" :value="item.nickname" :label="item.nickname" @click="handleSelect(item)" />
          </a-select>
          </a-space>
        </a-form-item>
        
        <a-form-item label="头像" field="avatar">
          <a-avatar 
          :src=avatar_url
            v-model="form.avatar"
            placeholder="头像"
          >
          <img :src="avatar_url" width="80"/>
          </a-avatar>
        </a-form-item>
        <a-form-item label="公众号ID" field="accountId">
          <a-input
            readonly='readonly'
            v-model="form.wx_id"
            placeholder="请输入公众号ID"
          >
            <template #prefix><icon-idcard /></template>
          </a-input>
        </a-form-item>
        
        <a-form-item label="描述" field="description">
          <a-textarea
            v-model="form.description"
            placeholder="请输入公众号描述"
            :auto-size="{ minRows: 3, maxRows: 5 }"
            allow-clear
          />
        </a-form-item>
        
        <a-form-item label="标签" field="tag_ids">
          <a-space>
            <a-input
              :model-value="selectedTagNames"
              placeholder="请选择标签（可选）"
              readonly
              style="width: 300px"
            />
            <a-button @click="showTagSelector = true">选择标签</a-button>
          </a-space>
        </a-form-item>
        
        <a-form-item>
          <a-space>
            <a-button type="primary" html-type="submit" :loading="loading">
              添加订阅
            </a-button>
            <a-button @click="resetForm">重置</a-button>
          </a-space>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
  
  <!-- 标签选择器模态框 -->
  <a-modal
    v-model:visible="showTagSelector"
    title="选择标签"
    :footer="false"
    width="800px"
  >
    <TagMultiSelect 
      ref="tagSelectorRef"
      v-model="form.tag_ids"
    />
    <template #footer>
      <a-button type="primary" @click="showTagSelector = false">确定</a-button>
    </template>
  </a-modal>
</template>

<script setup lang="ts">
import { ref, watch, computed } from 'vue'
import { useRouter } from 'vue-router'
import { Message, Modal } from '@arco-design/web-vue'
import { addSubscription,AddSubscriptionParams, searchBiz,getSubscriptionInfo } from '@/api/subscription'
import { listTags } from '@/api/tagManagement'
import {Avatar} from '@/utils/constants'
import TagMultiSelect from '@/components/TagMultiSelect.vue'
const router = useRouter()
const loading = ref(false)
const isFetching = ref(false)
const searchResults = ref([])
const avatar_url = ref('/static/default-avatar.png')
const formRef = ref(null)
const showTagSelector = ref(false)
const tagSelectorRef = ref<InstanceType<typeof TagMultiSelect> | null>(null)
const tagList = ref<any[]>([])

const form = ref({
  name: '',
  wx_id: '',
  avatar:'',
  description: '',
  tag_ids: [] as string[]
})

// 获取标签名称显示
const selectedTagNames = computed(() => {
  if (!form.value.tag_ids || form.value.tag_ids.length === 0) {
    return ''
  }
  const names = form.value.tag_ids.map(id => {
    const tag = tagList.value.find(t => t.id === id)
    return tag ? tag.name : id
  })
  return names.join(', ')
})

// 加载标签列表
const loadTags = async () => {
  try {
    const res = await listTags({ offset: 0, limit: 100 })
    // 处理不同的返回格式
    if (res && typeof res === 'object') {
      // 如果返回的是 {list: [], total: 0} 格式
      if ('list' in res) {
        tagList.value = res.list || []
      } 
      // 如果返回的是数组格式
      else if (Array.isArray(res)) {
        tagList.value = res
      }
      // 如果返回的是 {data: {list: []}} 格式
      else if (res.data && res.data.list) {
        tagList.value = res.data.list || []
      }
      else {
        tagList.value = []
      }
    } else {
      tagList.value = []
    }
  } catch (error: any) {
    console.error('加载标签列表失败:', error)
    const errorMsg = typeof error === 'string' ? error : (error?.message || '加载标签列表失败')
    Message.error(errorMsg)
    tagList.value = []
  }
}

// 监听 form.avatar 的变化
watch(() => form.value.avatar, (newValue, oldValue) => {
  console.log('头像地址已更新:', newValue);
  // 这里可以添加更多处理逻辑
  avatar_url.value=Avatar(newValue)
}, { deep: true });

const rules = {
  name: [
    { required: true, message: '请输入公众号名称' },
    { min: 2, max: 30, message: '公众号名称长度应在2-30个字符之间' }
  ],
  wx_id: [
    { required: true, message: '请输入公众号ID' },
    { pattern: /^[a-zA-Z0-9_-]+$/, message: '公众号ID只能包含字母、数字、下划线和横线' }
  ],
  avatar: [
    { 
      required: true, 
      message: '请选择公众号头像',
      validator: (value: string) => {
        return value && value.startsWith('http')
      },
      message: '请选择有效的头像URL'
    }
  ],
  description: [
    { max: 200, message: '描述不能超过200个字符' }
  ]
}

const handleSearch = async (value: string) => {
  if (!value) {
    searchResults.value = []
    return
  }
  try {
    const res = await searchBiz(value, {
      kw: value,
      offset: 0,
      limit: 10
    })
    searchResults.value = res.list || []
  } catch (error) {
    // Message.error('搜索公众号失败')
    searchResults.value = []
  }
}

const handleGetMpInfo = async () => {
  if (isFetching.value) return false;
  if (!articleLink.value) {
    Message.error('请提供一个公众号文章链接');
    return false;
  }
  isFetching.value = true;
  try {
    const res = await getSubscriptionInfo(articleLink.value.trim()); // 确保去除空格
    console.log('获取公众号信息:', res);
    const info=res?.mp_info||false
    if (info) {
      form.value.name = info.mp_name || '';
      form.value.description = info.mp_name || '';
      form.value.wx_id = info.biz || '';
      form.value.avatar = info.logo || '';
    }
  } catch (error) {
    console.error('获取公众号信息失败:', error);
    Message.error('获取公众号信息失败');
    return false;
  } finally {
    isFetching.value = false;
  }
  modalVisible.value = false;
  return true;
}

const handleSelect = (item: any) => {
  console.log(item)
  form.value.name = item.nickname
  form.value.wx_id = item.fakeid // 修正拼写错误：fackid → fakeid
  form.value.description = item.signature
  form.value.avatar = item.round_head_img
}

const handleSubmit = async () => {
  
  loading.value = true
  
  // 表单验证
  try {
    await formRef.value.validate()
  } catch (error) {
    Message.error(error?.errors?.join('\n') || '表单验证失败，请检查输入内容')
    loading.value = false
    return
  }

  // 表单提交
  try {
    await addSubscription({
      mp_name: form.value.name,
      mp_id: form.value.wx_id,
      avatar: form.value.avatar,
      mp_intro: form.value.description,
      tag_ids: form.value.tag_ids || []
    })
    
    Message.success('订阅添加成功')
    router.push('/')
  } catch (error) {
    console.error('订阅添加失败:', error)
    Message.error(error.message || '订阅添加失败，请稍后重试')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = {
    name: '',
    wx_id: '',
    avatar: '',
    description: '',
    tag_ids: []
  }
  searchResults.value = []
  if (tagSelectorRef.value) {
    tagSelectorRef.value.parseSelected([])
  }
}

// 初始化时加载标签列表
loadTags()

const modalVisible = ref(false);
const articleLink = ref('');

const openDialog = () => {
  modalVisible.value = true;
};


const goBack = () => {
  router.go(-1)
}
</script>

<style scoped>
.add-subscription {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.arco-form-item {
  margin-bottom: 20px;
}
</style>