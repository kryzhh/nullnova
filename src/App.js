import React, { useState, useEffect } from "react";
import "./App.css";
import NullNovaWebsite from "./components/landingpage";
import { SignedIn, SignedOut, SignInButton, UserButton } from '@clerk/clerk-react';
const App = () => {
   
  return (

      <NullNovaWebsite />
  )
}
export default App;
