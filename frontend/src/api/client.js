const API_URL = "http://localhost:8000";

// Real implementation with backend
// Login 

// export async function loginUser(email, password) {
//   const res = await fetch(`${API_URL}/auth/login`, {
    // method: "POST",
    // headers: {
    //   "Content-Type": "application/json",
    // },
    // body: JSON.stringify({ email, password }),
//   });
// 
//   if (!res.ok) {
    // const err = await res.json();
    // throw new Error(err.detail || "Login failed");
//   }
// 
//   return res.json();
// }

// Register 
// export async function registerUser(name, email, password) {
    // const res = await fetch("/api/register", {
    //   method: "POST",
    //   headers: { "Content-Type": "application/json" },
    //   body: JSON.stringify({ name, email, password }),
    // });
    // if (!res.ok) {
    //   const err = await res.json();
    //   throw new Error(err.detail || "Registration failed");
    // }
    // return res.json();
//   }

// Mock implementation for testing without backend
// Login
export async function loginUser(email, password) {
    // simulate network delay
    await new Promise((r) => setTimeout(r, 800));
  
    if (email === "test@mail.com" && password === "123456") {
      return {
        access_token: "fake-jwt-token-123"
      };
    }
  
    throw new Error("Invalid email or password");
  }

  // Register
    export async function registerUser(name, email, password) {
        // simulate network delay
        await new Promise((r) => setTimeout(r, 800));}