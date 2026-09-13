import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { verifyCertificate } from "@/api/certificates";
import BrandMark from "@/shared/components/BrandMark";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import Input from "@/shared/components/ui/Input";

const THEME_STORAGE_KEY = "learncode.theme";

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        month: "long",
        year: "numeric",
      }).format(new Date(value))
    : "Not specified";

export default function CertificateVerification() {
  const { verificationCode = "" } = useParams();
  const [code, setCode] = useState(verificationCode);
  const [submittedCode, setSubmittedCode] = useState(verificationCode);

  useEffect(() => {
    setCode(verificationCode);
    setSubmittedCode(verificationCode);
  }, [verificationCode]);

  useEffect(() => {
    window.localStorage.setItem(THEME_STORAGE_KEY, "light");
  }, []);

  const verificationQuery = useQuery({
    queryKey: ["certificate-verification", submittedCode],
    queryFn: () => verifyCertificate(submittedCode),
    enabled: Boolean(submittedCode),
    retry: false,
  });

  const result = verificationQuery.data;
  const issueDate = formatDate(result?.issue_date);
  const completionDate = formatDate(result?.completion_date);
  const verificationStatus = result?.verification_status;

  const handleSubmit = (event) => {
    event.preventDefault();
    setSubmittedCode(code.trim());
  };

  return (
    <div className="student-theme-root student-theme-light min-h-screen bg-lc-page px-4 py-6 text-ink">
      <div className="mx-auto flex min-h-[calc(100vh-3rem)] max-w-5xl flex-col">
        <header className="flex items-center justify-between gap-3">
          <Link
            to="/"
            className="inline-flex items-center gap-2.5 text-lg font-bold text-ocean-800"
          >
            <BrandMark />
            <span>LearnCode</span>
          </Link>
        </header>

        <main className="grid flex-1 items-center gap-6 py-8 lg:grid-cols-[1.05fr_0.95fr]">
          <section className="space-y-5">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocean-800 dark:text-reef">
                LearnCode Certificate Registry
              </p>
              <h1 className="mt-3 max-w-2xl text-3xl font-bold text-ink dark:text-sand sm:text-4xl">
                Verify official course completion.
              </h1>
              <p className="mt-3 max-w-xl text-sm leading-6 text-muted dark:text-reef/80">
                Enter the certificate verification code or scan the QR code printed on a LearnCode
                certificate.
              </p>
            </div>

            <Card variant="elevated" padding="lg">
              <form className="flex flex-col gap-3 sm:flex-row" onSubmit={handleSubmit}>
                <div className="flex-1">
                  <label
                    htmlFor="certificate-code"
                    className="mb-2 block text-xs font-semibold uppercase tracking-wide text-ocean-800 dark:text-reef"
                  >
                    Verification code
                  </label>
                  <Input
                    id="certificate-code"
                    value={code}
                    onChange={(event) => setCode(event.target.value)}
                    placeholder="Paste verification code"
                    className="w-full"
                  />
                </div>
                <Button
                  type="submit"
                  variant="gradient"
                  loading={verificationQuery.isFetching}
                  className="self-end"
                >
                  Verify
                </Button>
              </form>
            </Card>
          </section>

          <Card variant="elevated" padding="lg" className="overflow-hidden">
            <div className="-mx-6 -mt-6 mb-6 h-1.5 bg-gradient-to-r from-coral via-spice to-ocean-600" />
            {verificationQuery.isLoading ? (
              <p className="text-sm text-muted dark:text-reef/90">Checking certificate...</p>
            ) : verificationQuery.isError ? (
              <div className="space-y-3">
                <p className="inline-flex rounded-full border border-red-300/60 bg-red-50 px-3 py-1 text-xs font-bold uppercase text-red-800 dark:border-red-300/30 dark:bg-red-500/10 dark:text-red-100">
                  Verification unavailable
                </p>
                <p className="text-sm text-muted dark:text-reef/90">
                  Could not verify this certificate.
                </p>
              </div>
            ) : result?.valid ? (
              <div className="space-y-5">
                <p className="inline-flex rounded-full border border-emerald-300/60 bg-emerald-50 px-3 py-1 text-xs font-bold uppercase text-emerald-800 dark:border-emerald-300/30 dark:bg-emerald-400/10 dark:text-emerald-100">
                  Valid Certificate
                </p>
                <div>
                  <p className="text-xs font-semibold uppercase tracking-[0.16em] text-muted dark:text-reef/70">
                    Issued to
                  </p>
                  <h2 className="mt-1 text-2xl font-bold text-ink dark:text-sand">
                    {result.student_name}
                  </h2>
                  <p className="mt-3 text-sm leading-6 text-muted dark:text-reef/85">
                    {result.verification_summary || (
                      <>
                        This certificate confirms successful completion of
                        <span className="font-semibold text-ink dark:text-sand">
                          {" "}
                          {result.course_title}
                        </span>
                        .
                      </>
                    )}
                  </p>
                </div>
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Certificate number
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">
                      {result.certificate_number}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Issue date
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">{issueDate}</dd>
                  </div>
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Completion date
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">{completionDate}</dd>
                  </div>
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Status
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">
                      {result.certificate_status}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Organization
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">
                      {result.platform_name}
                    </dd>
                  </div>
                </dl>
              </div>
            ) : submittedCode && verificationStatus === "REVOKED" ? (
              <div className="space-y-4">
                <p className="inline-flex rounded-full border border-red-300/60 bg-red-50 px-3 py-1 text-xs font-bold uppercase text-red-800 dark:border-red-300/30 dark:bg-red-500/10 dark:text-red-100">
                  Certificate Revoked
                </p>
                <div>
                  <h2 className="text-xl font-bold text-ink dark:text-sand">
                    This certificate is no longer valid
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-muted dark:text-reef/85">
                    The registry found this certificate number, but it has been revoked by{" "}
                    {result.platform_name || "the issuing organization"}.
                  </p>
                </div>
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Certificate number
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">
                      {result.certificate_number}
                    </dd>
                  </div>
                  <div className="rounded-xl border border-ocean-600/10 bg-cream/80 p-3 dark:border-white/10 dark:bg-[#1b2b3b]/70">
                    <dt className="text-xs font-semibold uppercase tracking-wide text-muted dark:text-reef/75">
                      Status
                    </dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">
                      {result.certificate_status}
                    </dd>
                  </div>
                </dl>
              </div>
            ) : submittedCode ? (
              <div className="space-y-4">
                <p className="inline-flex rounded-full border border-red-300/60 bg-red-50 px-3 py-1 text-xs font-bold uppercase text-red-800 dark:border-red-300/30 dark:bg-red-500/10 dark:text-red-100">
                  Certificate Not Found
                </p>
                <div>
                  <h2 className="text-xl font-bold text-ink dark:text-sand">
                    This code could not be verified
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-muted dark:text-reef/85">
                    The verification code does not match an issued LearnCode certificate. Check the
                    code and try again.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <p className="inline-flex rounded-full border border-ocean-600/20 bg-reef/60 px-3 py-1 text-xs font-bold uppercase text-ocean-800 dark:border-white/10 dark:bg-[#1b2b3b] dark:text-reef">
                  Ready to verify
                </p>
                <div>
                  <h2 className="text-xl font-bold text-ink dark:text-sand">
                    Official verification
                  </h2>
                  <p className="mt-2 text-sm leading-6 text-muted dark:text-reef/85">
                    Scan a certificate QR code or enter a verification code to confirm authenticity.
                  </p>
                </div>
              </div>
            )}
          </Card>
        </main>
      </div>
    </div>
  );
}
