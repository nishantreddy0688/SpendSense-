export const API = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
export const token = () => typeof window !== "undefined" ? localStorage.getItem("spendsense_token") : null;
export async function request(path: string, init: RequestInit = {}) {
  const headers: Record<string,string> = { "Content-Type":"application/json", ...(init.headers as Record<string,string> || {}) };
  const value=token(); if(value) headers.Authorization=`Bearer ${value}`;
  const response=await fetch(`${API}${path}`,{...init,headers});
  if(!response.ok){let message="Something went wrong";try{message=(await response.json()).detail||message}catch{};throw new Error(message)}
  return response.status===204?null:response.json();
}
export async function uploadFile(path: string, file: File) {
  const body = new FormData(); body.append("file", file);
  const headers: Record<string,string> = {};
  const value=token(); if(value) headers.Authorization=`Bearer ${value}`;
  const response=await fetch(`${API}${path}`,{method:"POST",headers,body});
  if(!response.ok){let message="Unable to read this PDF";try{message=(await response.json()).detail||message}catch{};throw new Error(message)}
  return response.json();
}
