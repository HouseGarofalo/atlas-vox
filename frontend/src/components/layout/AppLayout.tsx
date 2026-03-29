import { Outlet } from "react-router-dom";
import Sidebar from "./Sidebar";
import Header from "./Header";

export default function AppLayout() {
  return (
    <div className="flex h-screen overflow-hidden">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden sidebar-offset">
        <Header />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6">
          <div style={{ maxWidth: 'var(--content-max-width)' }} className="mx-auto">
            <Outlet />
          </div>
        </main>
      </div>
    </div>
  );
}
