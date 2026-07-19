import client from "./client";

export const getCertificateEligibility = async (courseId) => {
  const { data } = await client.get(`/api/student/courses/${courseId}/certificate/eligibility/`);
  return data;
};

export const generateCertificate = async (courseId) => {
  const { data } = await client.post(`/api/student/courses/${courseId}/certificate/`);
  return data;
};

export const getMyCertificates = async () => {
  const { data } = await client.get("/api/certificates/my-certificates/");
  return data;
};

export const downloadCertificate = (certificateId) =>
  client.get(`/api/certificates/${certificateId}/download/`, { responseType: "blob" });

export const verifyCertificate = async (verificationCode) => {
  const { data } = await client.get(`/api/certificates/verify/${verificationCode}/`);
  return data;
};
