export interface MessageTask {
  id: string
  name: string
  message_template: string
  web_hook_url: string
  mps_id: string | null
  tag_ids?: string | null
  message_type: number
  status: number
  cron_exp?: string
  created_at: string
  updated_at: string
}

export interface MessageTaskCreate {
  name: string
  message_type: number
  message_template: string
  web_hook_url: string
  mps_id: any[]
  tag_ids: string[]
  status?: number
  cron_exp?: string
}

export interface MessageTaskSubmit {
  name: string
  message_type: number
  message_template: string
  web_hook_url: string
  mps_id: string
  tag_ids: string
  status?: number
  cron_exp?: string
}

export type MessageTaskUpdate = Partial<MessageTaskSubmit>