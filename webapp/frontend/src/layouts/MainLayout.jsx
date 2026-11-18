import { Outlet } from 'react-router-dom';
import { Footer } from '../components/layout/Footer.jsx';
import { Navbar } from '../components/layout/Navbar.jsx';

export function MainLayout() {
  return (
    <div className="flex min-h-screen flex-col bg-rr-plum text-rr-light">
      <Navbar />
      <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 py-6 sm:px-6 lg:px-8">
        <Outlet />
      </main>
      <Footer />
    </div>
  );
}

