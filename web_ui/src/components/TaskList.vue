<script setup lang="ts">
import { ref } from 'vue'
import type { MessageTask } from '@/types/messageTask'

const props = defineProps<{
  taskList: MessageTask[]
  loading: boolean
  pagination: {
    current: number
    pageSize: number
    total: number
  }
  isMobile: boolean
  tagMap?: Record<string, string>
}>()

const emit = defineEmits<{
  (e: 'pageChange', page: number): void
  (e: 'loadMore'): void
  (e: 'edit', id: string): void
  (e: 'test', id: string): void
  (e: 'run', id: string): void
  (e: 'delete', id: string): void
}>()

const parseCronExpression = (exp: string) => {
  const parts = exp.split(' ')
  if (parts.length !== 5) return exp
  
  const [minute, hour, day, month, week] = parts
  
  let result = ''
  
  // 解析分钟
  if (minute === '*') {
    result += '每分钟'
  } else if (minute.includes('/')) {
    const [_, interval] = minute.split('/')
    result += `每${interval}分钟`
  } else {
    result += `在${minute}分`
  }
  
  // 解析小时
  if (hour === '*') {
    result += '每小时'
  } else if (hour.includes('/')) {
    const [_, interval] = hour.split('/')
    result += `每${interval}小时`
  } else {
    result += ` ${hour}时`
  }
  
  // 解析日期
  if (day === '*') {
    result += ' 每天'
  } else if (day.includes('/')) {
    const [_, interval] = day.split('/')
    result += ` 每${interval}天`
  } else {
    result += ` ${day}日`
  }
  
  // 解析月份
  if (month === '*') {
    result += ' 每月'
  } else if (month.includes('/')) {
    const [_, interval] = month.split('/')
    result += ` 每${interval}个月`
  } else {
    result += ` ${month}月`
  }
  
  // 解析星期
  if (week !== '*') {
    result += ` 星期${week}`
  }
  
  return result || exp
}

const safeParse = (value: string | null | undefined) => {
  if (!value || typeof value !== 'string' || value.trim() === '') {
    return []
  }
  try {
    const parsed = JSON.parse(value)
    return Array.isArray(parsed) ? parsed : []
  } catch {
    return []
  }
}

const getMpSummary = (task: MessageTask) => {
  const data = safeParse(task.mps_id)
  if (data.length === 0) return ''
  const names = data
    .map((item: any) => item?.mp_name || item?.id)
    .filter(Boolean)
  if (names.length === 0) return ''
  return names.length > 3 ? `${names.slice(0, 3).join('、')} 等${names.length}个` : names.join('、')
}

const getTagSummary = (task: MessageTask) => {
  const ids = safeParse(task.tag_ids)
  if (ids.length === 0) return ''
  const names = ids
    .map((id: string) => props.tagMap?.[id] || id)
    .filter(Boolean)
  if (names.length === 0) return ''
  return names.length > 3 ? `${names.slice(0, 3).join('、')} 等${names.length}个` : names.join('、')
}
</script>

<template>
  <div>
    <a-table v-if="!props.isMobile"
      :data="taskList"
      :pagination="pagination"
      @page-change="emit('pageChange', $event)"
    >
      <template #columns>
        <a-table-column title="名称" data-index="name" ellipsis :width="200"/>
        <a-table-column title="cron表达式">
          <template #cell="{ record }">
            {{ parseCronExpression(record.cron_exp) }}
          </template>
        </a-table-column>
        <a-table-column title="类型" :width="100">
          <template #cell="{ record }">
            <a-tag :color="record.message_type === 1 ? 'green' : 'red'">
              {{ record.message_type === 1 ? 'WeekHook' : 'Message' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="目标">
          <template #cell="{ record }">
            <div v-if="getTagSummary(record)">标签：{{ getTagSummary(record) }}</div>
            <div v-if="getMpSummary(record)">公众号：{{ getMpSummary(record) }}</div>
            <div v-if="!getTagSummary(record) && !getMpSummary(record)">全部公众号</div>
          </template>
        </a-table-column>
        <a-table-column title="状态" :width="100">
          <template #cell="{ record }">
            <a-tag :color="record.status === 1 ? 'green' : 'red'">
              {{ record.status === 1 ? '启用' : '禁用' }}
            </a-tag>
          </template>
        </a-table-column>
        <a-table-column title="操作" :width="260">
          <template #cell="{ record }">
            <slot name="actions" :record="record"></slot>
          </template>
        </a-table-column>
      </template>
    </a-table>
    <a-list v-else :data="props.taskList" :bordered="false">
      <template #item="{ item }">
        <a-list-item>
          <a-list-item-meta>
            <template #title>
              {{ item.name }}
            </template>
            <template #description>
              <div>{{ parseCronExpression(item.cron_exp) }}</div>
              <div>
                <a-tag :color="item.message_type === 1 ? 'green' : 'red'">
                  {{ item.message_type === 1 ? 'WeekHook' : 'Message' }}
                </a-tag>
                <a-tag :color="item.status === 1 ? 'green' : 'red'">
                  {{ item.status === 1 ? '启用' : '禁用' }}
                </a-tag>
              </div>
              <div class="target-line">
                <template v-if="getTagSummary(item) || getMpSummary(item)">
                  <span v-if="getTagSummary(item)">标签：{{ getTagSummary(item) }}</span>
                  <span v-if="getMpSummary(item)">公众号：{{ getMpSummary(item) }}</span>
                </template>
                <template v-else>
                  全部公众号
                </template>
              </div>
            </template>
          </a-list-item-meta>
          
          <slot name="mobile-actions" :record="item"></slot>
        </a-list-item>
      </template>
      <template #footer>
        <div v-if="pagination.current * pagination.pageSize < pagination.total" class="load-more">
          <a-button type="primary" long :loading="loading" @click="emit('loadMore')">加载更多</a-button>
          <div class="total-count">
                共 {{ pagination.total }} 条
              </div>
        </div>
      </template>
    </a-list>
  </div>
</template>

<style scoped>
/* 移动端列表样式 */
.a-list {
  margin-top: 16px;
}

.a-list-item {
  padding: 12px 16px;
  margin-bottom: 8px;
  background-color: var(--color-bg-2);
  border-radius: 4px;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.1);
  transition: all 0.2s;
}

.a-list-item:hover {
  background-color: var(--color-bg-3);
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.a-list-item-meta-title {
  font-weight: 500;
  margin-bottom: 4px;
}

.a-list-item-meta-description {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.a-list-item-meta-description .arco-tag {
  margin-right: 8px;
}

.a-list-item-extra {
  display: flex;
  gap: 8px;
}

.target-line {
  margin-top: 8px;
  color: var(--color-text-2);
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.load-more{
    width: 120px;
    margin: 0px auto;
    text-align: center;
}
</style>