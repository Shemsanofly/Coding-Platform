import BrandMark from "@/shared/components/BrandMark";

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat(undefined, {
        day: "numeric",
        month: "long",
        year: "numeric",
      }).format(new Date(value))
    : "Not specified";

function Detail({ label, value }) {
  return (
    <div>
      <dt className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#5d6b78]">{label}</dt>
      <dd className="mt-1 text-xs font-semibold text-[#10212f]">{value || "Not specified"}</dd>
    </div>
  );
}

export default function CertificatePreview({ certificate }) {
  const platformName = certificate?.platform_name || "LearnCode";
  const issueYear = certificate?.issue_date ? new Date(certificate.issue_date).getFullYear() : new Date().getFullYear();

  return (
    <div className="mx-auto w-full max-w-6xl overflow-x-auto pb-2">
      <section
        className="relative mx-auto min-w-[820px] overflow-hidden bg-[#fffdf9] p-10 text-[#10212f] shadow-[0_24px_54px_rgba(16,33,47,0.16)]"
        style={{ aspectRatio: "297 / 210" }}
        aria-label="Certificate preview"
      >
        <div className="absolute inset-6 border-[3px] border-[#102c3d]" />
        <div className="absolute inset-9 border border-[#d9a441]" />
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
          <div className="flex h-52 w-52 items-center justify-center rounded-full border-2 border-[#d9a441]/10 text-7xl font-bold text-[#102c3d]/[0.035]">
            {platformName
              .split(/\s+/)
              .slice(0, 2)
              .map((part) => part[0])
              .join("")
              .toUpperCase() || "LC"}
          </div>
        </div>
        <div className="absolute left-12 top-12 h-12 w-12 border-l border-t border-[#d9a441]" />
        <div className="absolute right-12 top-12 h-12 w-12 border-r border-t border-[#d9a441]" />
        <div className="absolute bottom-12 left-12 h-12 w-12 border-b border-l border-[#d9a441]" />
        <div className="absolute bottom-12 right-12 h-12 w-12 border-b border-r border-[#d9a441]" />

        <div className="relative z-[1] flex items-start justify-between">
          <div className="flex w-52 items-center gap-3">
            <BrandMark className="!h-10 !w-10 !rounded-[10px] !border-[#d9a441] !bg-[#f7efe6] !text-[#102c3d]" />
            <div>
              <p className="text-sm font-bold text-[#102c3d]">{platformName}</p>
              <p className="text-[10px] text-[#5d6b78]">Official Learning Registry</p>
            </div>
          </div>
          <div className="text-center">
            <BrandMark className="mx-auto !h-12 !w-12 !rounded-[10px] !border-[#d9a441] !bg-[#f7efe6] !text-[#102c3d]" />
            <p className="mt-2 text-xs font-bold uppercase tracking-[0.18em] text-[#102c3d]">{platformName}</p>
            <p className="mt-0.5 text-[10px] text-[#5d6b78]">Certificate Registry</p>
          </div>
          <div className="w-52 text-right">
            <p className="text-[10px] font-bold uppercase tracking-[0.12em] text-[#5d6b78]">Certificate Number</p>
            <p className="mt-1 whitespace-nowrap text-xs font-bold text-[#102c3d]">{certificate?.certificate_number}</p>
          </div>
        </div>

        <div className="relative z-[1] mx-auto mt-7 max-w-3xl text-center">
          <h1 className="font-serif text-5xl font-bold uppercase tracking-normal text-[#102c3d]">Certificate</h1>
          <div className="mx-auto mt-2 h-px w-56 bg-[#d9a441]" />
          <p className="mt-3 text-sm font-bold uppercase tracking-[0.14em] text-[#d9a441]">Of Completion</p>
          <p className="mt-7 text-xs uppercase tracking-[0.16em] text-[#5d6b78]">This is to certify that</p>
          <p className="mx-auto mt-4 max-w-3xl break-words border-b border-[#d9a441] pb-2 font-serif text-4xl font-bold italic leading-tight text-[#10212f]">
            {certificate?.student_name}
          </p>
          <p className="mt-5 text-sm text-[#5d6b78]">
            has successfully completed all the prescribed requirements for the course
          </p>
          <p className="mx-auto mt-4 line-clamp-2 max-w-3xl break-words font-serif text-3xl font-bold leading-tight text-[#102c3d]">
            {certificate?.course_title}
          </p>
          <p className="mx-auto mt-4 max-w-2xl text-sm leading-6 text-[#5d6b78]">
            and is hereby awarded this Certificate of Completion in recognition of dedication, achievement, and
            successful completion of the programme.
          </p>
        </div>

        <div className="relative z-[1] mt-9 grid grid-cols-[1fr_auto_1fr] items-end gap-8">
          <div className="space-y-4">
            {certificate?.qr_code_data_url ? (
              <img
                src={certificate.qr_code_data_url}
                alt="Certificate verification QR code"
                className="h-32 w-32 border border-[#d6e2ea] bg-white p-2"
              />
            ) : (
              <div className="flex h-32 w-32 items-center justify-center border border-[#d6e2ea] bg-white text-center text-[10px] font-bold uppercase tracking-[0.12em] text-[#102c3d]">
                Generating
              </div>
            )}
            <p className="text-[10px] font-bold text-[#102c3d]">Scan to verify certificate</p>
            <p className="max-w-[12rem] break-words text-[10px] text-[#5d6b78]">{certificate?.verification_code}</p>
          </div>

          <div className="flex h-28 w-28 flex-col items-center justify-center rounded-full border-2 border-[#d9a441] text-center shadow-[inset_0_0_0_8px_rgba(217,164,65,0.12)]">
            <p className="text-[8px] font-bold uppercase text-[#102c3d]">Official Certificate</p>
            <p className="mt-1 text-xs font-bold uppercase text-[#d9a441]">Verified</p>
            <p className="mt-1 text-[10px] font-bold text-[#5d6b78]">{issueYear}</p>
          </div>

          <div className="text-center">
            <div className="mx-auto flex h-14 w-52 items-end justify-center border-b border-[#102c3d] text-[10px] uppercase tracking-[0.12em] text-[#5d6b78]">
              Signature
            </div>
            <p className="mt-2 text-sm font-bold text-[#10212f]">{certificate?.ceo_name || "Shemsa Amin"}</p>
            <p className="text-xs text-[#5d6b78]">{certificate?.ceo_title || "Chief Executive Officer"}</p>
          </div>
        </div>

        <dl className="relative z-[1] mt-4 grid grid-cols-4 gap-3 border-t border-[#d9a441]/40 pt-3">
          <Detail label="Date issued" value={formatDate(certificate?.issue_date)} />
          <Detail label="Completion date" value={formatDate(certificate?.completion_date)} />
          <Detail label="Instructor" value={certificate?.instructor_name} />
          <Detail label="Duration" value={certificate?.course_duration} />
        </dl>

        <p className="relative z-[1] mt-4 text-center text-[10px] leading-4 text-[#5d6b78]">
          This certificate is issued electronically by {platformName}. Its authenticity may be verified by scanning the
          QR code or entering the verification code on the official verification page.
        </p>
      </section>
    </div>
  );
}
