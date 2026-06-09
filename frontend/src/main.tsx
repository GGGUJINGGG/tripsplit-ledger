import React from "react";
import ReactDOM from "react-dom/client";
import { createBrowserRouter, RouterProvider } from "react-router-dom";

import App from "./App";
import SettlementPage from "./pages/SettlementPage";
import TripDetailPage from "./pages/TripDetailPage";
import TripsPage from "./pages/TripsPage";
import "./styles/global.css";

const router = createBrowserRouter([
  {
    path: "/",
    element: <App />,
    children: [
      { index: true, element: <TripsPage /> },
      { path: "trips/:tripId", element: <TripDetailPage /> },
      { path: "trips/:tripId/settlements", element: <SettlementPage /> },
    ],
  },
]);

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <RouterProvider router={router} />
  </React.StrictMode>,
);
