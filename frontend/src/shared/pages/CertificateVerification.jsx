import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useParams } from "react-router-dom";
import { verifyCertificate } from "@/api/certificates";
import BrandMark from "@/shared/components/BrandMark";
import Button from "@/shared/components/ui/Button";
import Card from "@/shared/components/ui/Card";
import Input from "@/shared/components/ui/Input";

export default function CertificateVerification() {
  const { verificationCode = "" } = useParams();
  const [code, setCode] = useState(verificationCode);
  const [submittedCode, setSubmittedCode] = useState(verificationCode);

  useEffect(() => {
    setCode(verificationCode);
    setSubmittedCode(verificationCode);
  }, [verificationCode]);

  const verificationQuery = useQuery({
    queryKey: ["certificate-verification", submittedCode],
    queryFn: () => verifyCertificate(submittedCode),
    enabled: Boolean(submittedCode),
    retry: false,
  });

  const result = verificationQuery.data;
  const issueDate = result?.issue_date ? new Date(result.issue_date).toLocaleDateString() : "";

  const handleSubmit = (event) => {
    event.preventDefault();
    setSubmittedCode(code.trim());
  };

  return (
    <div className="min-h-screen bg-lc-page px-4 py-8 text-ink dark:bg-lc-page-dark dark:text-sand">
      <div className="mx-auto max-w-3xl space-y-6">
        <Link to="/" className="inline-flex items-center gap-2.5 text-lg font-bold text-ocean-800 dark:text-reef">
          <BrandMark />
          <span>LearnCode</span>
        </Link>

        <Card variant="elevated" padding="lg">
          <p className="text-xs font-semibold uppercase tracking-widest text-ocean-800 dark:text-reef">
            Certificate Verification
          </p>
          <h1 className="mt-2 text-2xl font-bold text-ink dark:text-sand">Verify a certificate</h1>

          <form className="mt-5 flex flex-col gap-3 sm:flex-row" onSubmit={handleSubmit}>
            <div className="flex-1">
              <Input
                value={code}
                onChange={(event) => setCode(event.target.value)}
                placeholder="Verification code"
                className="w-full"
              />
            </div>
            <Button type="submit" variant="gradient" loading={verificationQuery.isFetching}>
              Verify
            </Button>
          </form>
        </Card>

        {submittedCode ? (
          <Card variant="elevated" padding="lg">
            {verificationQuery.isLoading ? (
              <p className="text-sm text-muted dark:text-reef/90">Checking certificate...</p>
            ) : verificationQuery.isError ? (
              <p className="text-sm text-red-600 dark:text-red-200">Could not verify this certificate.</p>
            ) : result?.valid ? (
              <div className="space-y-3">
                <p className="inline-flex rounded-full bg-emerald-100 px-3 py-1 text-xs font-semibold uppercase text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100">
                  Valid Certificate
                </p>
                <div>
                  <h2 className="text-xl font-bold text-ink dark:text-sand">{result.student_name}</h2>
                  <p className="mt-1 text-sm text-muted dark:text-reef/90">{result.course_title}</p>
                </div>
                <dl className="grid gap-3 text-sm sm:grid-cols-2">
                  <div>
                    <dt className="text-xs uppercase text-muted dark:text-reef/80">Certificate number</dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">{result.certificate_number}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted dark:text-reef/80">Issue date</dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">{issueDate}</dd>
                  </div>
                  <div>
                    <dt className="text-xs uppercase text-muted dark:text-reef/80">Status</dt>
                    <dd className="mt-1 font-semibold text-ink dark:text-sand">{result.certificate_status}</dd>
                  </div>
                </dl>
              </div>
            ) : (
              <div className="space-y-2">
                <p className="inline-flex rounded-full bg-red-100 px-3 py-1 text-xs font-semibold uppercase text-red-800 dark:bg-red-500/20 dark:text-red-100">
                  Invalid Certificate
                </p>
                <p className="text-sm text-muted dark:text-reef/90">
                  This verification code is not active or does not match an issued certificate.
                </p>
              </div>
            )}
          </Card>
        ) : null}
      </div>
    </div>
  );
}
