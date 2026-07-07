import { Navigate } from "react-router-dom";

export default function Recommendations() {
  return <Navigate to="/learning-path?tab=suggestions" replace />;
}
