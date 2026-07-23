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
import BrandMark from "@/shared/components/BrandMark";
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
        <section className="space-y-4">
          <SectionHeader title="Certificates" subtitle={`${certificates.length} issued by LearnCode`} />
          <ul className="grid gap-4">
            {certificates.map((certificate) => {
              const issueDate = certificate.issue_date
                ? new Date(certificate.issue_date).toLocaleDateString()
                : "";
              return (
                <li
                  key={certificate.id}
                  className="overflow-hidden rounded-2xl border border-ocean-600/10 bg-white shadow-lg dark:border-white/10 dark:bg-[#172433]/85 dark:shadow-[0_22px_46px_rgba(5,18,30,0.26)]"
                >
                  <div className="h-1.5 bg-gradient-to-r from-coral via-spice to-ocean-600" />
                  <div className="flex flex-col gap-5 p-5 sm:flex-row sm:items-center sm:justify-between">
                    <div className="flex min-w-0 gap-4">
                      <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl border border-ocean-600/10 bg-reef/70 dark:border-white/10 dark:bg-[#213548]">
                        <BrandMark />
                      </div>
                      <div className="min-w-0">
                        <p className="text-xs font-semibold uppercase tracking-[0.14em] text-ocean-800 dark:text-reef">
                          LearnCode Certificate Registry
                        </p>
                        <h2 className="mt-1 truncate text-lg font-bold text-ink dark:text-sand">
                          {certificate.course_title}
                        </h2>
                        <dl className="mt-3 grid gap-2 text-xs text-muted dark:text-reef/80 sm:grid-cols-2">
                          <div>
                            <dt className="font-semibold uppercase tracking-wide">Certificate no.</dt>
                            <dd className="mt-0.5 font-medium text-ink dark:text-sand">
                              {certificate.certificate_number}
                            </dd>
                          </div>
                          <div>
                            <dt className="font-semibold uppercase tracking-wide">Issued</dt>
                            <dd className="mt-0.5 font-medium text-ink dark:text-sand">{issueDate || "Available"}</dd>
                          </div>
                        </dl>
                      </div>
                    </div>
                    <div className="flex flex-wrap items-center gap-2 sm:justify-end">
                      <span className="inline-flex min-h-8 items-center rounded-full border border-emerald-300/60 bg-emerald-50 px-3 text-xs font-bold uppercase text-emerald-800 dark:border-emerald-300/30 dark:bg-emerald-400/10 dark:text-emerald-100">
                        {certificate.status}
                      </span>
                      <Button
                        variant="gradient"
                        size="sm"
                        loading={downloadMutation.isPending}
                        onClick={() => downloadMutation.mutate(certificate.id)}
                      >
                        Download
                      </Button>
                      <Link
                        to={`/certificates/${certificate.id}`}
                        className="inline-flex min-h-9 items-center rounded-xl border border-ocean-600/20 px-3 text-xs font-semibold text-ocean-800 transition hover:bg-reef/40 dark:border-white/10 dark:bg-[#1b2b3b]/75 dark:text-reef dark:hover:bg-[#213548]"
                      >
                        View
                      </Link>
                      <Link
                        to={`/verify-certificate/${certificate.verification_code}`}
                        className="inline-flex min-h-9 items-center rounded-xl border border-ocean-600/20 px-3 text-xs font-semibold text-ocean-800 transition hover:bg-reef/40 dark:border-white/10 dark:bg-[#1b2b3b]/75 dark:text-reef dark:hover:bg-[#213548]"
                      >
                        Verify
                      </Link>
                    </div>
                  </div>
                </li>
              );
            })}
          </ul>
        </section>
      )}
    </div>
  );
}
