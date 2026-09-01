import React from "react";
import ReactDOM from "react-dom/client";
import {
  createBrowserRouter,
  RouterProvider,
} from "react-router-dom";

import App from "./App";
import LoginPage from "./pages/LoginPage";
import SettlementPage from "./pages/SettlementPage";
import TripDetailPage from "./pages/TripDetailPage";
import TripsPage from "./pages/TripsPage";
import "./styles/global.css";
import RegisterPage from "./pages/RegisterPage";
import { AuthProvider } from "./auth/AuthContext";
import ProtectedRoute from "./auth/ProtectedRoute";

const router = createBrowserRouter([
  {
    path: "/login",
    element: <LoginPage />,
  },
  {
    path: "/register",
    element: <RegisterPage />,
  },
  {
    element: <ProtectedRoute />,
    children: [
      {
        path: "/",
        element: <App />,
        children: [
          {
            index: true,
            element: <TripsPage />,
          },
          {
            path: "trips/:tripId",
            element: <TripDetailPage />,
          },
          {
            path: "trips/:tripId/settlements",
            element: <SettlementPage />,
          },
        ],
      },
    ],
  },
]);


ReactDOM.createRoot(
  document.getElementById("root")!,
).render(
  <React.StrictMode>
    <AuthProvider>
      <RouterProvider router={router} />
    </AuthProvider>
  </React.StrictMode>,
);