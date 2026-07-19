import { useMutation, useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import toast from "react-hot-toast";
import { downloadCertificate, getMyCertificates } from "@/api/certificates";
import LoadingState from "@/student/components/LoadingState";
import SectionHeader from "@/student/components/SectionHeader";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import PageHeader from "@/shared/components/ui/PageHeader";
import ErrorState from "@/shared/components/ErrorState";
import { triggerBlobDownload } from "@/shared/utils/downloadBlob";

export default function MyCertificates() {
  const certificatesQuery = useQuery({
    queryKey: ["my-certificates"],
    queryFn: getMyCertificates,
  });

  const downloadMutation = useMutation({
    mutationFn: (certificateId) => downloadCertificate(certificateId),
    onSuccess: (response) => triggerBlobDownload(response, "certificate.pdf"),
    onError: () => toast.error("Could not download certificate.", { id: "my-certificate-download-error" }),
  });

  const certificates = Array.isArray(certificatesQuery.data) ? certificatesQuery.data : [];

  return (
    <div className="space-y-6 overflow-x-hidden p-4 md:p-6">
      <PageHeader
        title="My Certificates"
        subtitle="Download completed course certificates and open their verification pages."
      />

      {certificatesQuery.isLoading ? (
        <LoadingState label="Loading certificates..." rows={4} />
      ) : certificatesQuery.isError ? (
        <ErrorState message="Could not load certificates." onRetry={() => void certificatesQuery.refetch()} />
      ) : certificates.length === 0 ? (
        <Card variant="subtle">
          <p className="text-sm text-muted dark:text-reef/90">
            Completed course certificates will appear here.
          </p>
        </Card>
      ) : (
        <Card variant="elevated">
          <SectionHeader title="Certificates" subtitle={`${certificates.length} issued`} />
          <ul className="mt-4 divide-y divide-line dark:divide-line/30">
            {certificates.map((certificate) => {
              const issueDate = certificate.issue_date
                ? new Date(certificate.issue_date).toLocaleDateString()
                : "";
              return (
                <li
                  key={certificate.id}
                  className="flex flex-col gap-3 py-4 first:pt-0 last:pb-0 sm:flex-row sm:items-center sm:justify-between"
                >
                  <div className="min-w-0">
                    <p className="font-semibold text-ink dark:text-sand">{certificate.course_title}</p>
                    <p className="mt-1 text-xs text-muted dark:text-reef/90">
                      {certificate.certificate_number} {issueDate ? `- Issued ${issueDate}` : ""}
                    </p>
                    <p className="mt-1 text-xs font-medium uppercase text-ocean-800 dark:text-reef">
                      {certificate.status}
                    </p>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <Button
                      variant="gradient"
                      size="sm"
                      loading={downloadMutation.isPending}
                      onClick={() => downloadMutation.mutate(certificate.id)}
                    >
                      Download
                    </Button>
                    <Link
                      to={`/verify-certificate/${certificate.verification_code}`}
                      className="inline-flex min-h-9 items-center rounded-xl border border-ocean-600/20 px-3 text-xs font-semibold text-ocean-800 transition hover:bg-reef/40 dark:border-line/40 dark:text-reef dark:hover:bg-ocean-900/50"
                    >
                      View
                    </Link>
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      )}
    </div>
  );
}
