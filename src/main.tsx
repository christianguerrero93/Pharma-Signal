import React from 'react';
import ReactDOM from 'react-dom/client';
import EnterpriseDSPApp from './EnterpriseDSPApp';
import './styles.css';
import './dspContinuation.css';
import './enterpriseDsp.css';

ReactDOM.createRoot(document.getElementById('root') as HTMLElement).render(
  <React.StrictMode>
    <EnterpriseDSPApp />
  </React.StrictMode>,
);
