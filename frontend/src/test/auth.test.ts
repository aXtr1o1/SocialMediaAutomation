import { describe, expect, it, vi } from 'vitest'

const { apiFetch } = vi.hoisted(() => ({
  apiFetch: vi.fn(),
}))

vi.mock('../lib/api', () => ({
  apiFetch,
}))

const { supabase } = vi.hoisted(() => ({
  supabase: {
    auth: {
      signInWithOAuth: vi.fn(),
      setSession: vi.fn(),
    },
  },
}))

vi.mock('../lib/supabaseClient', () => ({
  supabase,
}))

import { changePassword } from '../lib/auth'

describe('changePassword', () => {
  it('sends sign_out_all_devices=true when requested', async () => {
    apiFetch.mockResolvedValue({
      message: 'ok',
      signed_out_all_devices: true,
    })

    const result = await changePassword({
      currentPassword: 'old',
      newPassword: 'new-password',
      confirmPassword: 'new-password',
      signOutAllDevices: true,
    })

    expect(result.signed_out_all_devices).toBe(true)

    expect(apiFetch).toHaveBeenCalledWith(
      '/auth/change-password',
      expect.objectContaining({
        method: 'POST',
        body: JSON.stringify({
          current_password: 'old',
          new_password: 'new-password',
          confirm_password: 'new-password',
          sign_out_all_devices: true,
        }),
      }),
    )
  })
})