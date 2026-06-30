import { getDisplayName, getInitials, getProfileImageUrl } from "@/shared/utils/userDisplay";

export default function UserAvatar({ user, size = "md", className = "" }) {
  const imageUrl = getProfileImageUrl(user);
  const initials = getInitials(user);
  const label = getDisplayName(user);

  const sizeClasses = {
    sm: "h-9 w-9 text-xs",
    md: "h-14 w-14 text-lg",
    lg: "h-20 w-20 text-xl",
  };

  const base = `flex shrink-0 items-center justify-center overflow-hidden rounded-2xl bg-gradient-to-br from-coral to-ocean-600 font-bold text-white ${sizeClasses[size] ?? sizeClasses.md} ${className}`;

  if (imageUrl) {
    return (
      <img
        src={imageUrl}
        alt={`${label} profile`}
        className={`${base} object-cover`}
      />
    );
  }

  return (
    <span className={base} aria-hidden="true">
      {initials}
    </span>
  );
}
