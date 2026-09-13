import { useMutation, useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import toast from "react-hot-toast";
import { downloadCertificate, getCertificate } from "@/api/certificates";
import CertificatePreview from "@/student/components/CertificatePreview";
import LoadingState from "@/student/components/LoadingState";
import ErrorState from "@/shared/components/ErrorState";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import PageHeader from "@/shared/components/ui/PageHeader";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

export default function CertificateDetail() {
  const { certificateId } = useParams();
  const id = Number(certificateId);

  const certificateQuery = useQuery({
    queryKey: ["certificate", id],
    queryFn: () => getCertificate(id),
    enabled: Number.isFinite(id),
    retry: false,
  });

  const downloadMutation = useMutation({
    mutationFn: () => downloadCertificate(id),
    onSuccess: (response) => triggerBlobDownload(response, "certificate.pdf"),
    onError: () =>
      toast.error("Could not download certificate.", { id: "certificate-detail-download-error" }),
  });

  const certificate = certificateQuery.data;
  const isActive = certificate?.status === "ACTIVE";

  if (!Number.isFinite(id)) {
    return (
      <div className="p-6">
        <ErrorState title="Invalid certificate" message="This certificate link is not valid." />
      </div>
    );
  }

  return (
    <div className="space-y-6 overflow-x-hidden p-4 md:p-6">
      <PageHeader
        title="Certificate Preview"
        subtitle="Read-only preview of your official completion certificate."
        actions={
          <>
            <Link className="lc-btn-ghost min-h-10 px-4" to="/certificates">
              Back
            </Link>
            <Button
              variant="gradient"
              loading={downloadMutation.isPending}
              onClick={() => downloadMutation.mutate()}
            >
              Download PDF
            </Button>
          </>
        }
      />

      {certificateQuery.isLoading ? (
        <LoadingState label="Loading certificate..." rows={5} />
      ) : certificateQuery.isError ? (
        <ErrorState
          message="Could not load this certificate."
          onRetry={() => void certificateQuery.refetch()}
        />
      ) : (
        <>
          <Card variant="subtle" className="flex flex-wrap items-center justify-between gap-3">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ocean-800 dark:text-reef">
                Verification status
              </p>
              <p className="mt-1 text-sm text-muted dark:text-reef/80">
                {isActive
                  ? "This certificate is active in the LearnCode registry."
                  : "This certificate is not currently active."}
              </p>
            </div>
            <span
              className={`inline-flex min-h-8 items-center rounded-full border px-3 text-xs font-bold uppercase ${
                isActive
                  ? "border-emerald-300/60 bg-emerald-50 text-emerald-800 dark:border-emerald-300/30 dark:bg-emerald-400/10 dark:text-emerald-100"
                  : "border-red-300/60 bg-red-50 text-red-800 dark:border-red-300/30 dark:bg-red-500/10 dark:text-red-100"
              }`}
            >
              {certificate.status}
            </span>
          </Card>

          <CertificatePreview certificate={certificate} />
        </>
      )}
    </div>
  );
}
