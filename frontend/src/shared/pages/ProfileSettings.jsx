import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import toast from "react-hot-toast";
import { useAuth } from "@/context/AuthProvider";
import { updateProfile } from "@/api/auth";
import UserAvatar from "@/shared/components/UserAvatar";

const EXPERIENCE_LEVELS = [
  { value: "beginner", label: "Beginner" },
  { value: "intermediate", label: "Intermediate" },
  { value: "advanced", label: "Advanced" },
];

function extractApiError(error) {
  const data = error?.response?.data;
  if (!data) {
    return "Could not save settings.";
  }
  if (typeof data.detail === "string") {
    return data.detail;
  }
  const firstKey = Object.keys(data)[0];
  const value = data[firstKey];
  if (Array.isArray(value) && value.length) {
    return String(value[0]);
  }
  if (typeof value === "string") {
    return value;
  }
  return "Could not save settings.";
}

export default function ProfileSettings({
  heading = "Settings",
  description = "Update your name and profile photo.",
}) {
  const { user, refreshUserProfile } = useAuth();
  const fileInputRef = useRef(null);

  const [firstName, setFirstName] = useState("");
  const [lastName, setLastName] = useState("");
  const [experienceLevel, setExperienceLevel] = useState("beginner");
  const [previewUrl, setPreviewUrl] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [removePhoto, setRemovePhoto] = useState(false);

  useEffect(() => {
    setFirstName(user?.first_name ?? "");
    setLastName(user?.last_name ?? "");
    setExperienceLevel(user?.experience_level ?? "beginner");
    setPreviewUrl(null);
    setSelectedFile(null);
    setRemovePhoto(false);
  }, [user]);

  const saveMutation = useMutation({
    mutationFn: updateProfile,
    onSuccess: async (updatedUser) => {
      await refreshUserProfile(updatedUser);
      toast.success("Settings saved.", { id: "settings-save-ok" });
      setSelectedFile(null);
      setPreviewUrl(null);
      setRemovePhoto(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
    },
    onError: (error) => {
      toast.error(extractApiError(error), { id: "settings-save-err" });
    },
  });

  const handleFileChange = (event) => {
    const file = event.target.files?.[0];
    if (!file) {
      return;
    }
    if (!file.type.startsWith("image/")) {
      toast.error("Please choose an image file.");
      event.target.value = "";
      return;
    }
    if (file.size > 2 * 1024 * 1024) {
      toast.error("Image must be 2 MB or smaller.");
      event.target.value = "";
      return;
    }
    setSelectedFile(file);
    setRemovePhoto(false);
    setPreviewUrl(URL.createObjectURL(file));
  };

  useEffect(() => {
    return () => {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
      }
    };
  }, [previewUrl]);

  const handleSubmit = (event) => {
    event.preventDefault();
    if (saveMutation.isPending) {
      return;
    }

    const payload = new FormData();
    payload.append("first_name", firstName.trim());
    payload.append("last_name", lastName.trim());
    if (user?.role === "student") {
      payload.append("experience_level", experienceLevel);
    }
    if (removePhoto) {
      payload.append("remove_profile_image", "true");
    } else if (selectedFile) {
      payload.append("profile_image", selectedFile);
    }

    saveMutation.mutate(payload);
  };

  const previewUser = {
    ...user,
    first_name: firstName,
    last_name: lastName,
    full_name: `${firstName} ${lastName}`.trim() || user?.full_name,
    profile_image_url: previewUrl || (removePhoto ? null : user?.profile_image_url),
  };

  const hasExistingPhoto = Boolean(user?.profile_image_url);
  const showRemovePhoto = hasExistingPhoto && !selectedFile;

  return (
    <div className="space-y-6 overflow-x-hidden p-4 md:p-6">
      <header className="min-w-0">
        <h1 className="text-2xl font-bold text-ink dark:text-sand">{heading}</h1>
        <p className="mt-1 text-sm text-muted dark:text-muted">{description}</p>
      </header>

      <form
        onSubmit={handleSubmit}
        className="max-w-xl space-y-6 rounded-2xl border border-ocean-600/10 bg-white p-5 shadow-sm dark:border-line/30 dark:bg-ocean-950/40"
      >
        <section className="flex flex-wrap items-center gap-4">
          <UserAvatar user={previewUser} size="lg" />
          <div className="min-w-0 flex-1 space-y-2">
            <p className="text-sm font-semibold text-ink dark:text-sand">Profile photo</p>
            <p className="text-xs text-muted">JPG, PNG, WebP, or GIF. Max 2 MB.</p>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                className="inline-flex min-h-10 items-center rounded-xl border border-ocean-200 px-4 text-sm font-semibold text-ocean-800 hover:bg-reef/40 dark:border-ocean-600/40 dark:text-reef dark:hover:bg-ocean-600/10"
              >
                Upload photo
              </button>
              {showRemovePhoto ? (
                <button
                  type="button"
                  onClick={() => {
                    setRemovePhoto(true);
                    setSelectedFile(null);
                    setPreviewUrl(null);
                    if (fileInputRef.current) {
                      fileInputRef.current.value = "";
                    }
                  }}
                  className="inline-flex min-h-10 items-center rounded-xl border border-coral/30 px-4 text-sm font-semibold text-coral hover:bg-coral/10"
                >
                  Remove photo
                </button>
              ) : null}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png,image/webp,image/gif"
              className="hidden"
              onChange={handleFileChange}
            />
          </div>
        </section>

        <section className="grid gap-4 sm:grid-cols-2">
          <div>
            <label
              htmlFor="settings-first-name"
              className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef"
            >
              First name
            </label>
            <input
              id="settings-first-name"
              type="text"
              autoComplete="given-name"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              className="lc-input"
              maxLength={150}
            />
          </div>
          <div>
            <label
              htmlFor="settings-last-name"
              className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef"
            >
              Last name
            </label>
            <input
              id="settings-last-name"
              type="text"
              autoComplete="family-name"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
              className="lc-input"
              maxLength={150}
            />
          </div>
        </section>

        <div>
          <label
            htmlFor="settings-email"
            className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef"
          >
            Email
          </label>
          <input
            id="settings-email"
            type="email"
            value={user?.email ?? ""}
            disabled
            className="lc-input cursor-not-allowed opacity-70"
          />
          <p className="mt-1 text-xs text-muted">
            Email is used to sign in and cannot be changed here.
          </p>
        </div>

        {user?.role === "student" ? (
          <div>
            <label
              htmlFor="settings-level"
              className="mb-1.5 block text-sm font-semibold text-ocean-800 dark:text-reef"
            >
              Learning level
            </label>
            <select
              id="settings-level"
              value={experienceLevel}
              onChange={(event) => setExperienceLevel(event.target.value)}
              className="lc-input"
            >
              {EXPERIENCE_LEVELS.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </div>
        ) : null}

        <div className="flex flex-wrap gap-2 pt-2">
          <button
            type="submit"
            disabled={saveMutation.isPending}
            className="lc-btn-primary min-h-10 px-5"
          >
            {saveMutation.isPending ? "Saving..." : "Save changes"}
          </button>
        </div>
      </form>
    </div>
  );
}
