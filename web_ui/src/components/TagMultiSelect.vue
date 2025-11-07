<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { listTags } from '@/api/tagManagement'
import type { Tag } from '@/types/tagManagement'
import { Message } from '@arco-design/web-vue'

const props = defineProps({
  modelValue: {
    type: Array as () => string[],
    default: () => []
  }
})

const emit = defineEmits(['update:modelValue'])

const searchKeyword = ref('')
const loading = ref(false)
const tagList = ref<Tag[]>([])
const selectedTagIds = ref<string[]>([])

const filteredTags = computed(() => {
  if (!searchKeyword.value) {
    return tagList.value.filter(tag => 
      !selectedTagIds.value.includes(tag.id)
    )
  }
  return tagList.value.filter(tag => 
    !selectedTagIds.value.includes(tag.id) &&
    tag.name.toLowerCase().includes(searchKeyword.value.toLowerCase())
  )
})

const fetchTags = async () => {
  loading.value = true
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
    console.error('获取标签列表失败:', error)
    const errorMsg = typeof error === 'string' ? error : (error?.message || '获取标签列表失败')
    Message.error(errorMsg)
    tagList.value = []
  } finally {
    loading.value = false
  }
}

const toggleSelect = (tag: Tag) => {
  const index = selectedTagIds.value.findIndex(id => id === tag.id)
  if (index === -1) {
    selectedTagIds.value.push(tag.id)
  } else {
    selectedTagIds.value.splice(index, 1)
  }
  emitSelectedIds()
}

const removeSelected = (tagId: string) => {
  selectedTagIds.value = selectedTagIds.value.filter(id => id !== tagId)
  emitSelectedIds()
}

const clearAll = () => {
  selectedTagIds.value = []
  emitSelectedIds()
}

const selectAll = () => {
  filteredTags.value.forEach(tag => {
    if (!selectedTagIds.value.includes(tag.id)) {
      selectedTagIds.value.push(tag.id)
    }
  })
  emitSelectedIds()
}

const emitSelectedIds = () => {
  emit('update:modelValue', selectedTagIds.value)
}

const parseSelected = (data: string[]) => {
  selectedTagIds.value = [...data]
}

defineExpose({
  parseSelected
})

onMounted(() => {
  fetchTags()
  if (props.modelValue && props.modelValue.length > 0) {
    parseSelected(props.modelValue)
  }
})
</script>

<template>
  <a-card class="tag-multi-select" :bordered="false">
    <a-space direction="vertical" fill>
      <a-space>
        <a-input
          v-model="searchKeyword"
          placeholder="搜索标签"
          allow-clear
        />
      </a-space>

      <a-spin :loading="loading">
        <template v-if="!loading && tagList.length === 0">
          <a-empty description="暂无标签，请先创建标签" />
        </template>
        <template v-else>
          <template v-if="selectedTagIds.length > 0">
            <a-space align="center" class="title-line">
              <h4>已选标签 ({{ selectedTagIds.length }})</h4>
              <a-button size="mini" type="text" @click="clearAll">清空</a-button>
            </a-space>
            <a-space wrap>
              <a-tag
                v-for="tagId in selectedTagIds"
                :key="tagId"
                closable
                @close="removeSelected(tagId)"
              >
                {{ tagList.find(t => t.id === tagId)?.name || tagId }}
              </a-tag>
            </a-space>
          </template>

          <a-space align="center" class="title-line">
            <h4>可选标签</h4>
            <a-button size="mini" type="text" @click="selectAll" :disabled="filteredTags.length === 0">全选</a-button>
          </a-space>
          <div class="tag-list">
            <template v-if="filteredTags.length === 0">
              <a-empty description="没有可选的标签" />
            </template>
            <div
              v-for="tag in filteredTags"
              :key="tag.id"
              class="tag-item"
              :class="{ 'tag-item-selected': selectedTagIds.includes(tag.id) }"
              @click="toggleSelect(tag)"
            >
              <a-space>
                <img 
                  v-if="tag.cover" 
                  :src="tag.cover" 
                  alt="cover"
                  class="tag-cover"
                />
                <span>{{ tag.name }}</span>
                <a-tag v-if="tag.status === 0" size="small" color="red">禁用</a-tag>
              </a-space>
            </div>
          </div>
        </template>
      </a-spin>
    </a-space>
  </a-card>
</template>

<style scoped>
.tag-multi-select {
  padding: 15px;
}
.title-line {
  width: 100%;
}
h4 {
  margin-bottom: 10px;
  display: block;
  font-size: 14px;
  color: var(--color-text-2);
}

.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag-item {
  padding: 6px 12px;
  border-radius: 4px;
  cursor: pointer;
  background-color: var(--color-fill-1);
  border-radius: 2rem;
  transition: all 0.2s;
}

.tag-item:hover {
  background-color: var(--color-fill-2);
}

.tag-item-selected {
  background-color: var(--color-primary-light-1);
  border: 1px solid var(--color-primary);
}

.tag-cover {
  width: 20px;
  height: 20px;
  border-radius: 4px;
  object-fit: cover;
}
</style>

