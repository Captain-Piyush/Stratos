import React from 'react';
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom';
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
        <div style={{ display: 'flex', flexDirection: 'column', height: '100vh', backgroundColor: 'var(--bg-main)' }}>
            <nav style={{ 
                display: 'flex', alignItems: 'center', padding: '0 24px', height: '60px', 
                backgroundColor: 'var(--bg-dark)', borderBottom: '1px solid var(--border-color)', gap: '32px'
            }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <Activity size={24} color="var(--accent-blue)" />
                    <h1 style={{ margin: 0, fontSize: '1.2rem', color: 'var(--text-main)', letterSpacing: '0.05em' }}>
                        STRATOS
                    </h1>
                </div>
                
                <div style={{ display: 'flex', gap: '24px', fontSize: '14px', flex: 1 }}>
                    <Link to="/" className={isLinkActive('/')}>Overview</Link>
                    <Link to="/methodology" className={isLinkActive('/methodology')}>Methodology</Link>
                    <Link to="/calibration" className={isLinkActive('/calibration')}>Calibration</Link>
                    <Link to="/validation" className={isLinkActive('/validation')}>Validation</Link>
                    <Link to="/architecture" className={isLinkActive('/architecture')}>Architecture</Link>
                </div>

                <div>
                    <Link to="/demo" style={{ 
                        padding: '8px 16px', backgroundColor: 'var(--accent-blue)', color: '#000', 
                        borderRadius: '4px', fontWeight: 600, textDecoration: 'none'
                    }}>
                        Launch Race Console Demo
                    </Link>
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
                    <Route path="/methodology" element={<Methodology />} />
                    <Route path="/calibration" element={<Calibration />} />
                    <Route path="/validation" element={<Validation />} />
                    <Route path="/architecture" element={<Architecture />} />
                    <Route path="/demo" element={<RaceConsole />} />
                </Routes>
            </NavLayout>
        </BrowserRouter>
    );
}

export default App;
