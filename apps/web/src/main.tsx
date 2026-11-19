import React from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import App from './App';
import '@cct/ui/styles.css';
import './web.css';

createRoot(document.getElementById('root')!).render(<BrowserRouter basename={import.meta.env.BASE_URL.replace(/\/$/, "") || "/"}><App/></BrowserRouter>);
