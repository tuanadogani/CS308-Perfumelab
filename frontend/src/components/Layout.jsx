import { Outlet } from 'react-router-dom';
import Navbar from './Navbar';

export default function Layout() {
  return (
    <>
      <Navbar />
      <main><Outlet /></main>
      <footer className="footer">
        <div className="container footer__inner">
          <span className="logo">Maison <em>Lumière</em></span>
          <span className="muted small">CS 308 Online Store · {new Date().getFullYear()}</span>
        </div>
      </footer>
    </>
  );
}
