export function getDisplayName(user) {
  const full = user?.full_name?.trim();
  if (full) {
    return full;
  }
  const combined = `${user?.first_name ?? ""} ${user?.last_name ?? ""}`.trim();
  if (combined) {
    return combined;
  }
  return user?.email?.split("@")[0] || "User";
}

export function getInitials(user) {
  const name = getDisplayName(user);
  const parts = name.split(/\s+/).filter(Boolean);
  if (parts.length >= 2) {
    return `${parts[0][0]}${parts[1][0]}`.toUpperCase();
  }
  return name.slice(0, 2).toUpperCase();
}

export function getProfileImageUrl(user) {
  return user?.profile_image_url || null;
}
