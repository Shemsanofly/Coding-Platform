import { useLayoutEffect, useRef, useState } from "react";
import BrandMark from "@/shared/components/BrandMark";

const CERTIFICATE_WIDTH = 1200;
const CERTIFICATE_HEIGHT = 800;

function clean(value, fallback = "") {
  return typeof value === "string" && value.trim() ? value.trim() : fallback;
}

function formatCertificateDate(value) {
  if (!value) {
    return "AUGUST 28, 2026";
  }

  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return "AUGUST 28, 2026";
  }

  return parsed
    .toLocaleDateString("en-US", {
      month: "long",
      day: "numeric",
      year: "numeric",
    })
    .toUpperCase();
}

function fitTextSize(text, large, medium, small) {
  if (text.length > 64) return small;
  if (text.length > 34) return medium;
  return large;
}

export default function CertificatePreview({ certificate }) {
  const shellRef = useRef(null);
  const [scale, setScale] = useState(1);

  useLayoutEffect(() => {
    const shell = shellRef.current;
    if (!shell) return undefined;

    const resize = () => {
      const nextScale = Math.min(1, shell.clientWidth / CERTIFICATE_WIDTH);
      setScale(Number.isFinite(nextScale) && nextScale > 0 ? nextScale : 1);
    };

    resize();
    const observer = new ResizeObserver(resize);
    observer.observe(shell);
    return () => observer.disconnect();
  }, []);

  const recipientName = clean(certificate?.student_name, "Shemsa Amin");
  const courseTitle = clean(certificate?.course_title, "Introduction to HTML");
  const certificateId = clean(certificate?.certificate_number, "LC-2026-0828-76573DEE");
  const platformName = clean(certificate?.platform_name, "LearnCode").toUpperCase();
  const platformWebsite = clean(certificate?.platform_website, "learncode.platform");
  const instructorName = clean(certificate?.instructor_name, "Course Instructor");
  const ceoName = clean(certificate?.ceo_name, "Shemsa Amin");
  const ceoTitle = clean(certificate?.ceo_title, "Chief Executive Officer");
  const issueDate = formatCertificateDate(certificate?.issue_date);
  const completionDate = formatCertificateDate(certificate?.completion_date || certificate?.issue_date);
  const qrCode = clean(certificate?.qr_code_data_url);

  return (
    <div ref={shellRef} className="w-full overflow-hidden">
      <style>
        {`
          .lc-cert-stage {
            width: ${CERTIFICATE_WIDTH}px;
            height: ${CERTIFICATE_HEIGHT}px;
            position: relative;
            transform-origin: top left;
            color: #10212f;
            background: linear-gradient(135deg, #d8eef6 0%, #ffffff 48%, #f7efe6 100%);
            box-shadow: 0 28px 62px rgba(16, 33, 47, 0.18);
            overflow: hidden;
            font-family: "Space Grotesk", "Segoe UI", sans-serif;
          }

          .lc-cert-stage,
          .lc-cert-stage * {
            box-sizing: border-box;
          }

          .lc-cert-shape {
            position: absolute;
            transform: skewX(-18deg);
          }

          .lc-cert-shape-1 { left: -94px; top: 0; width: 470px; height: 212px; background: #0f4c75; }
          .lc-cert-shape-2 { left: -42px; top: 0; width: 290px; height: 152px; background: #15608d; opacity: .98; }
          .lc-cert-shape-3 { left: 245px; top: 0; width: 245px; height: 76px; background: #22b7ad; opacity: .82; }
          .lc-cert-shape-4 { left: 430px; top: 0; width: 250px; height: 70px; background: #ff6f61; opacity: .72; }
          .lc-cert-shape-5 { right: -90px; bottom: 0; width: 438px; height: 198px; background: #13658f; }
          .lc-cert-shape-6 { right: 168px; bottom: 0; width: 270px; height: 84px; background: #22b7ad; opacity: .8; }
          .lc-cert-shape-7 { left: 126px; bottom: 0; width: 280px; height: 112px; background: #d9a441; opacity: .9; }
          .lc-cert-shape-8 { left: 376px; bottom: 0; width: 280px; height: 76px; background: #ff6f61; opacity: .68; }

          .lc-cert-paper {
            position: absolute;
            left: 74px;
            top: 70px;
            width: 1052px;
            height: 660px;
            background:
              radial-gradient(circle at 50% 50%, rgba(216, 238, 246, .74), transparent 32%),
              linear-gradient(135deg, rgba(255, 255, 255, .98), rgba(255, 253, 249, .99));
            border: 1px solid rgba(255, 255, 255, .94);
            box-shadow: 0 22px 44px rgba(16, 33, 47, .12);
            overflow: hidden;
          }

          .lc-cert-paper::before {
            content: "";
            position: absolute;
            inset: 0;
            background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='112' height='28' viewBox='0 0 112 28'%3E%3Cpath d='M0 15c18-10 38-10 56 0s38 10 56 0' fill='none' stroke='%2315608d' stroke-opacity='.07' stroke-width='3'/%3E%3C/svg%3E");
            background-size: 112px 28px;
          }

          .lc-cert-paper::after {
            content: "";
            position: absolute;
            inset: 28px;
            border: 1px solid rgba(217, 164, 65, .55);
            box-shadow: 0 0 0 14px rgba(216, 238, 246, .45);
          }

          .lc-cert-watermark {
            position: absolute;
            left: 50%;
            top: 50%;
            width: 330px;
            height: 330px;
            transform: translate(-50%, -50%);
            border-radius: 999px;
            border: 18px solid rgba(21, 96, 141, .035);
          }

          .lc-cert-content {
            position: absolute;
            left: 74px;
            top: 70px;
            width: 1052px;
            height: 660px;
            padding: 32px 72px 28px;
            display: grid;
            grid-template-rows: 96px 360px 144px;
          }

          .lc-cert-header {
            display: grid;
            grid-template-columns: 230px 1fr 250px;
            align-items: start;
          }

          .lc-cert-verified {
            display: inline-flex;
            align-items: center;
            gap: 9px;
            min-height: 34px;
            border: 1px solid rgba(217, 164, 65, .75);
            background: rgba(255, 255, 255, .92);
            padding: 8px 12px;
            color: #0f4c75;
            font-size: 14px;
            font-weight: 800;
            text-transform: uppercase;
            box-shadow: 0 6px 16px rgba(16, 33, 47, .08);
          }

          .lc-cert-verified-dot {
            width: 10px;
            height: 10px;
            border-radius: 999px;
            background: #ff6f61;
          }

          .lc-cert-brand {
            text-align: center;
          }

          .lc-cert-brand-row {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: 12px;
          }

          .lc-cert-brand .lc-brand-icon {
            width: 42px;
            height: 42px;
            color: #15608d;
            background: #d8eef6;
            border-color: rgba(21, 96, 141, .22);
          }

          .lc-cert-brand-name {
            color: #102c3d;
            font-size: 27px;
            line-height: 1;
            font-weight: 800;
          }

          .lc-cert-site {
            margin-top: 8px;
            color: #5d6b78;
            font-size: 16px;
            font-weight: 600;
          }

          .lc-cert-id-top {
            text-align: right;
          }

          .lc-cert-label {
            color: #5d6b78;
            font-size: 13px;
            line-height: 1;
            font-weight: 800;
            text-transform: uppercase;
          }

          .lc-cert-id-value {
            margin-top: 9px;
            color: #102c3d;
            font-size: 19px;
            line-height: 1.18;
            font-weight: 800;
            overflow-wrap: anywhere;
          }

          .lc-cert-main {
            text-align: center;
          }

          .lc-cert-title {
            margin: 0;
            color: #15608d;
            font-family: Georgia, "Times New Roman", serif;
            font-size: 76px;
            line-height: .95;
            font-weight: 500;
            white-space: nowrap;
          }

          .lc-cert-subtitle {
            width: 650px;
            margin: 22px auto 0;
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 18px;
          }

          .lc-cert-subtitle-line {
            height: 2px;
            flex: 1;
            background: #15608d;
          }

          .lc-cert-subtitle-text {
            color: #10212f;
            font-size: 22px;
            line-height: 1;
            font-weight: 800;
            text-transform: uppercase;
          }

          .lc-cert-present {
            margin: 44px 0 0;
            color: #10212f;
            font-size: 23px;
            line-height: 1.2;
            font-weight: 800;
            text-transform: uppercase;
          }

          .lc-cert-recipient {
            width: 760px;
            min-height: 76px;
            margin: 20px auto 0;
            padding-bottom: 10px;
            border-bottom: 2px solid rgba(217, 164, 65, .72);
            color: #15608d;
            font-family: Georgia, "Times New Roman", serif;
            font-style: italic;
            line-height: 1;
            overflow-wrap: anywhere;
          }

          .lc-cert-course {
            width: 820px;
            margin: 22px auto 0;
            color: #5d6b78;
            font-size: 30px;
            line-height: 1.18;
            font-weight: 700;
            overflow-wrap: anywhere;
          }

          .lc-cert-course strong {
            color: #102c3d;
            font-weight: 800;
          }

          .lc-cert-footer {
            display: grid;
            grid-template-columns: 260px 300px 1fr 92px;
            align-items: end;
            gap: 28px;
          }

          .lc-cert-rule {
            width: 220px;
            height: 2px;
            background: #15608d;
          }

          .lc-cert-person {
            margin: 14px 0 0;
            color: #10212f;
            font-size: 21px;
            line-height: 1.12;
            font-weight: 800;
            text-transform: uppercase;
            overflow-wrap: anywhere;
          }

          .lc-cert-role {
            margin: 8px 0 0;
            color: #5d6b78;
            font-size: 16px;
            line-height: 1.1;
            font-weight: 700;
            text-transform: uppercase;
          }

          .lc-cert-signature {
            text-align: center;
          }

          .lc-cert-signature svg {
            display: block;
            width: 238px;
            height: 64px;
            margin: 0 auto;
          }

          .lc-cert-signature-rule {
            width: 238px;
            height: 2px;
            margin: 0 auto;
            background: #15608d;
          }

          .lc-cert-signature-label {
            margin: 10px 0 0;
            color: #d9a441;
            font-size: 14px;
            line-height: 1;
            font-weight: 800;
            text-transform: uppercase;
          }

          .lc-cert-signer {
            margin: 8px 0 0;
            color: #10212f;
            font-size: 17px;
            line-height: 1.08;
            font-weight: 800;
          }

          .lc-cert-signer-title {
            margin: 4px 0 0;
            color: #5d6b78;
            font-size: 13px;
            line-height: 1.08;
            font-weight: 700;
          }

          .lc-cert-details {
            margin: 0;
            text-align: right;
          }

          .lc-cert-details div + div {
            margin-top: 11px;
          }

          .lc-cert-details dt {
            color: #10212f;
            font-size: 13px;
            line-height: 1;
            font-weight: 800;
            text-transform: uppercase;
          }

          .lc-cert-details dd {
            margin: 5px 0 0;
            color: #5d6b78;
            font-size: 16px;
            line-height: 1.15;
            font-weight: 700;
            overflow-wrap: anywhere;
          }

          .lc-cert-qr {
            text-align: center;
          }

          .lc-cert-qr-box {
            width: 92px;
            height: 92px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: #ffffff;
            border: 1px solid #d6e2ea;
            box-shadow: 0 6px 14px rgba(16, 33, 47, .08);
          }

          .lc-cert-qr-box img {
            width: 74px;
            height: 74px;
            object-fit: contain;
          }

          .lc-cert-qr-fallback {
            color: #15608d;
            font-size: 18px;
            line-height: 1;
            font-weight: 800;
          }

          .lc-cert-verify-text {
            margin: 8px 0 0;
            color: #0f4c75;
            font-size: 12px;
            line-height: 1;
            font-weight: 800;
            text-transform: uppercase;
          }
        `}
      </style>

      <div
        className="mx-auto"
        style={{
          width: CERTIFICATE_WIDTH * scale,
          height: CERTIFICATE_HEIGHT * scale,
        }}
      >
        <article
          className="lc-cert-stage"
          style={{ transform: `scale(${scale})` }}
          aria-label={`Certificate of completion for ${recipientName}`}
        >
          <span className="lc-cert-shape lc-cert-shape-1" />
          <span className="lc-cert-shape lc-cert-shape-2" />
          <span className="lc-cert-shape lc-cert-shape-3" />
          <span className="lc-cert-shape lc-cert-shape-4" />
          <span className="lc-cert-shape lc-cert-shape-5" />
          <span className="lc-cert-shape lc-cert-shape-6" />
          <span className="lc-cert-shape lc-cert-shape-7" />
          <span className="lc-cert-shape lc-cert-shape-8" />

          <div className="lc-cert-paper">
            <span className="lc-cert-watermark" />
          </div>

          <div className="lc-cert-content">
            <header className="lc-cert-header">
              <div>
                <div className="lc-cert-verified">
                  <span className="lc-cert-verified-dot" />
                  VERIFIED 2026
                </div>
              </div>

              <div className="lc-cert-brand">
                <div className="lc-cert-brand-row">
                  <BrandMark />
                  <span className="lc-cert-brand-name">{platformName}</span>
                </div>
                <p className="lc-cert-site">{platformWebsite}</p>
              </div>

              <div className="lc-cert-id-top">
                <p className="lc-cert-label">Certificate ID</p>
                <p className="lc-cert-id-value">{certificateId}</p>
              </div>
            </header>

            <main className="lc-cert-main">
              <h1 className="lc-cert-title">C E R T I F I C A T E</h1>
              <div className="lc-cert-subtitle">
                <span className="lc-cert-subtitle-line" />
                <span className="lc-cert-subtitle-text">Of Completion</span>
                <span className="lc-cert-subtitle-line" />
              </div>

              <p className="lc-cert-present">We proudly present this certificate to</p>
              <p className="lc-cert-recipient" style={{ fontSize: fitTextSize(recipientName, 60, 48, 38) }}>
                {recipientName}
              </p>
              <p className="lc-cert-course" style={{ fontSize: fitTextSize(courseTitle, 30, 26, 22) }}>
                for completing the course <strong>{courseTitle}</strong>
              </p>
            </main>

            <footer className="lc-cert-footer">
              <div>
                <div className="lc-cert-rule" />
                <p className="lc-cert-person">{instructorName}</p>
                <p className="lc-cert-role">Course Speaker</p>
              </div>

              <div className="lc-cert-signature">
                <svg viewBox="0 0 260 78" aria-hidden="true">
                  <path
                    d="M18 48 C43 8, 69 67, 98 25 S151 60, 178 35 S215 18, 242 23"
                    fill="none"
                    stroke="#10212f"
                    strokeLinecap="round"
                    strokeWidth="5"
                  />
                </svg>
                <div className="lc-cert-signature-rule" />
                <p className="lc-cert-signature-label">Authorized Signature</p>
                <p className="lc-cert-signer">{ceoName}</p>
                <p className="lc-cert-signer-title">{ceoTitle}</p>
              </div>

              <dl className="lc-cert-details">
                <div>
                  <dt>Issuing Date</dt>
                  <dd>{issueDate}</dd>
                </div>
                <div>
                  <dt>Course Completed</dt>
                  <dd>{completionDate}</dd>
                </div>
                <div>
                  <dt>Certificate ID</dt>
                  <dd>{certificateId}</dd>
                </div>
              </dl>

              <div className="lc-cert-qr">
                <div className="lc-cert-qr-box">
                  {qrCode ? (
                    <img
                      src={qrCode}
                      alt="Certificate verification QR code"
                      onError={(event) => {
                        event.currentTarget.style.visibility = "hidden";
                      }}
                    />
                  ) : (
                    <span className="lc-cert-qr-fallback">QR</span>
                  )}
                </div>
                <p className="lc-cert-verify-text">Verify</p>
              </div>
            </footer>
          </div>
        </article>
      </div>
    </div>
  );
}
