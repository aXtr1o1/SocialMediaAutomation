import { supabase } from './supabaseClient'

const AVATAR_BUCKET = 'avatars'
const MAX_BYTES = 2 * 1024 * 1024
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp', 'image/gif'])

function extensionForType(type: string) {
  if (type === 'image/png') {
    return 'png'
  }
  if (type === 'image/webp') {
    return 'webp'
  }
  if (type === 'image/gif') {
    return 'gif'
  }
  return 'jpg'
}

function isUploadedAvatarUrl(url: string | null | undefined, userId: string) {
  if (!url) {
    return false
  }
  return url.includes(`/storage/v1/object/public/${AVATAR_BUCKET}/${userId}/`)
}

export async function uploadProfileAvatar(file: File) {
  if (!ALLOWED_TYPES.has(file.type)) {
    throw new Error('Use a JPG, PNG, WEBP, or GIF image.')
  }
  if (file.size > MAX_BYTES) {
    throw new Error('Image must be 2 MB or smaller.')
  }

  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser()

  if (userError || !user) {
    throw new Error('You need to sign in again.')
  }

  const ext = extensionForType(file.type)
  const path = `${user.id}/avatar.${ext}`

  const { error: uploadError } = await supabase.storage.from(AVATAR_BUCKET).upload(path, file, {
    upsert: true,
    contentType: file.type,
    cacheControl: '3600',
  })

  if (uploadError) {
    throw new Error(
      uploadError.message.includes('Bucket not found')
        ? 'Avatar storage is not set up. Run the avatars SQL migration in Supabase.'
        : uploadError.message || 'Could not upload photo',
    )
  }

  const { data } = supabase.storage.from(AVATAR_BUCKET).getPublicUrl(path)
  const publicUrl = `${data.publicUrl}?t=${Date.now()}`

  const { error: updateError } = await supabase.auth.updateUser({
    data: {
      avatar_url: publicUrl,
      picture: publicUrl,
    },
  })

  if (updateError) {
    throw updateError
  }

  return publicUrl
}

export async function removeProfileAvatar() {
  const {
    data: { user },
    error: userError,
  } = await supabase.auth.getUser()

  if (userError || !user) {
    throw new Error('You need to sign in again.')
  }

  const currentUrl =
    (typeof user.user_metadata?.avatar_url === 'string' && user.user_metadata.avatar_url) ||
    (typeof user.user_metadata?.picture === 'string' && user.user_metadata.picture) ||
    null

  if (isUploadedAvatarUrl(currentUrl, user.id)) {
    const { data: files } = await supabase.storage.from(AVATAR_BUCKET).list(user.id)
    const paths = (files || []).map((file) => `${user.id}/${file.name}`)
    if (paths.length) {
      await supabase.storage.from(AVATAR_BUCKET).remove(paths)
    }
  }

  const { error: updateError } = await supabase.auth.updateUser({
    data: {
      avatar_url: '',
      picture: '',
    },
  })

  if (updateError) {
    throw updateError
  }
}
