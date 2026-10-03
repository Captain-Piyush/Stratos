import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation, Navigate } from 'react-router-dom';
import { RaceConsole } from './pages/RaceConsole';
import { Overview } from './pages/Overview';
import { Methodology } from './pages/Methodology';
import { Validation } from './pages/Validation';
import { Calibration } from './pages/Calibration';
import { Architecture } from './pages/Architecture';
import { Activity } from 'lucide-react';
import './index.css';

function NavLayout({ children }: { children: React.ReactNode }) {
    const loc = useLocation();
    const isLinkActive = (path: string) => loc.pathname === path ? 'active-link' : '';

    return (
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-dark)' }}>
            <nav style={{ 
                display: 'flex', alignItems: 'center', padding: '0 16px', height: '40px', 
                backgroundColor: 'var(--bg-panel)', borderBottom: '1px solid var(--border-color)', gap: '24px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Activity size={16} color="var(--accent-cyan)" />
                    <h1 style={{ margin: 0, fontSize: '14px', color: 'var(--text-bright)', letterSpacing: '0.1em' }}>
                        STRATOS
                    </h1>
                </div>
                
                <div style={{ display: 'flex', gap: '16px', flex: 1 }}>
                    <Link to="/" className={isLinkActive('/')}>Overview</Link>
                    <Link to="/console" className={isLinkActive('/console')}>Race Console</Link>
                    <Link to="/calibration" className={isLinkActive('/calibration')}>Calibration</Link>
                    <Link to="/validation" className={isLinkActive('/validation')}>Validation</Link>
                    <Link to="/methodology" className={isLinkActive('/methodology')}>Methodology</Link>
                    <Link to="/architecture" className={isLinkActive('/architecture')}>Architecture</Link>
                </div>
            </nav>
            <div style={{ flex: 1, overflow: 'auto' }}>
                {children}
            </div>
        </div>
    );
}

function App() {
    return (
        <BrowserRouter>
            <NavLayout>
                <Routes>
                    <Route path="/" element={<Overview />} />
                    <Route path="/console" element={<RaceConsole />} />
                    <Route path="/calibration" element={<Calibration />} />
                    <Route path="/validation" element={<Validation />} />
                    <Route path="/methodology" element={<Methodology />} />
                    <Route path="/architecture" element={<Architecture />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
            </NavLayout>
        </BrowserRouter>
    );
}

export default App;
