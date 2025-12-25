import React from "react";
import { BrowserRouter as Router, Routes, Route, Outlet, useLocation, matchPath } from "react-router-dom";
import AdminDashboard from "./components/AdminDashboard";
import HomePage from "./components/HomePage";
import SignUpPage from "./components/SignUpPage";
import LoginPage from "./components/LoginPage";
import ServicesSection from "./components/ServicesSection";
import AboutPage from "./components/AboutPage";
import ContactPage from "./components/ContactPage";
import WorkerApplicationPage from "./components/WorkerApplicationPage";
import Navbar from "./components/Navbar";
import UserHomePage from "./components/UserHomePage";
import WorkerHomePage from "./components/WorkerHomePage";
import ProfileCompletionPage from "./components/ProfileCompletionPage";
import { GeoapifyContext } from "@geoapify/react-geocoder-autocomplete";

// Verifier imports
import ApplicationList from './components/Verifier1/ApplicationList';
import ApplicationDetail from './components/Verifier1/ApplicationDetail';
import ApplicationList2 from './components/Verifier2/ApplicationList2';
import ApplicationDetail2 from './components/Verifier2/ApplicationDetail2';
import ApplicationList3 from './components/Verifier3/ApplicationList3';
import ApplicationDetail3 from './components/Verifier3/ApplicationDetail3';

function Layout() {
  const location = useLocation();

  // Routes where Navbar is hidden
  const hideNavbarPaths = [
    "/userhome",
    "/admin",
    "/workerhome",
    "/reset-password/:uid/:token",
    "/add",
    "/complete-address",
    "/verifier1",
    "/verifier1/applications/:id",
    "/verifier2",
    "/verifier2/applications/:id",
    "/verifier3",
    "/verifier3/applications/:id"
  ];

  const showNavbar = !hideNavbarPaths.some(pattern =>
    matchPath({ path: pattern, end: true }, location.pathname)
  );

  return (
    <>
      {showNavbar && <Navbar />}
      <main className={showNavbar ? "pt-12" : ""}>
        <Outlet />
      </main>
    </>
  );
}

function App() {
  return (
    <GeoapifyContext apiKey="1dec767eff4b49419346e6adb2815a1d">
      <Router>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<HomePage />} />
            <Route path="/signup" element={<SignUpPage />} />
            <Route path="/login" element={<LoginPage />} />
            <Route path="/services" element={<ServicesSection />} />
            <Route path="/about" element={<AboutPage />} />
            <Route path="/contact" element={<ContactPage />} />
            <Route path="/worker-application" element={<WorkerApplicationPage />} />
            <Route path="/workerhome" element={<WorkerHomePage />} />
            <Route path="/reset-password/:uid/:token" element={<LoginPage />} />
            <Route path="/userhome" element={<UserHomePage />} />
            <Route path="/admin" element={<AdminDashboard />} />
            <Route path="/complete-address" element={<ProfileCompletionPage />} />

            {/* Verifier 1 Routes */}
            <Route path="/verifier1" element={<ApplicationList />} />
            <Route path="/verifier1/applications/:id" element={<ApplicationDetail />} />

            {/* Verifier 2 Routes */}
            <Route path="/verifier2" element={<ApplicationList2 />} />
            <Route path="/verifier2/applications/:id" element={<ApplicationDetail2 />} />

            {/* Verifier 3 Routes */}
            <Route path="/verifier3" element={<ApplicationList3 />} />
            <Route path="/verifier3/applications/:id" element={<ApplicationDetail3 />} />
          </Route>
        </Routes>
      </Router>
    </GeoapifyContext>
  );
}

export default App;
