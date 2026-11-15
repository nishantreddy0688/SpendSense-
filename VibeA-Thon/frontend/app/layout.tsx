import "./globals.css";
import type { Metadata } from "next";
export const metadata: Metadata = { title: "SpendSense — Money, made clear", description: "A calmer way to understand your money." };
export default function RootLayout({children}:{children:React.ReactNode}) { return <html lang="en"><body>{children}</body></html> }
