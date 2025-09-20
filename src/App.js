import React from "react";
import { BrowserRouter as Router, Routes, Route } from "react-router-dom";
import NullNovaWebsite from "./components/landingpage";
import VerifyPage from "./components/verifypage";

const App = () => {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<NullNovaWebsite />} />
        <Route path="/verify" element={<VerifyPage />} />
      </Routes>
    </Router>
  );
};

export default App;
