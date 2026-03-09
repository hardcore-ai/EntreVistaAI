"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import Cookies from "js-cookie";
import { LayoutDashboard, Megaphone, Users, LogOut } from "lucide-react";

const nav = [
  { href: "/dashboard", label: "Resumen", icon: LayoutDashboard },
  { href: "/dashboard/campaigns", label: "Campañas", icon: Megaphone },
  { href: "/dashboard/candidates", label: "Cola HITL", icon: Users },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();

  function logout() {
    Cookies.remove("token");
    router.push("/login");
  }

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="w-64 bg-brand-900 text-white flex flex-col">
        <div className="p-6 border-b border-brand-700">
          <h1 className="text-xl font-bold">EntreVista AI</h1>
          <p className="text-brand-200 text-xs mt-0.5">Panel de reclutadores</p>
        </div>
        <nav className="flex-1 p-4 space-y-1">
          {nav.map(({ href, label, icon: Icon }) => {
            const active = pathname === href || (href !== "/dashboard" && pathname.startsWith(href));
            return (
              <Link
                key={href}
                href={href}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  active ? "bg-brand-700 text-white" : "text-brand-200 hover:bg-brand-800 hover:text-white"
                }`}
              >
                <Icon className="w-4 h-4" />
                {label}
              </Link>
            );
          })}
        </nav>
        <div className="p-4 border-t border-brand-700">
          <button
            onClick={logout}
            className="flex items-center gap-2 text-brand-200 hover:text-white text-sm w-full"
          >
            <LogOut className="w-4 h-4" />
            Cerrar sesión
          </button>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  );
}
