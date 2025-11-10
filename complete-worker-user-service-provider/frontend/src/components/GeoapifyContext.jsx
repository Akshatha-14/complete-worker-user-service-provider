import React, { createContext, useContext, useCallback } from 'react';

const GeoapifyContext = createContext();

const API_KEY = "1dec767eff4b49419346e6adb2815a1d";
const BASE_URL = "https://api.geoapify.com/v1/geocode/search";

export const GeoapifyProvider = ({ children }) => {

  // Function to geocode an address to { lat, lon }
  const geocodeAddress = useCallback(async (address) => {
    if (!address) return null;

    try {
      const url = `${BASE_URL}?text=${encodeURIComponent(address)}&format=json&apiKey=${API_KEY}`;
      const response = await fetch(url);
      const data = await response.json();

      if (data.features && data.features.length > 0) {
        const [lon, lat] = data.features[0].geometry.coordinates;
        return { lat, lon };
      }
      return null;

    } catch (error) {
      console.error("Geoapify geocoding error:", error);
      return null;
    }
  }, []);

  return (
    <GeoapifyContext.Provider value={{ apiKey: API_KEY, geocodeAddress }}>
      {children}
    </GeoapifyContext.Provider>
  );
};

// Custom hook for consuming context
export const useGeoapify = () => {
  return useContext(GeoapifyContext);
};
