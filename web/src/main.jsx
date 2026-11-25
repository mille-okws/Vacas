import React from 'react';
import {createRoot} from 'react-dom/client';
import '@astryxdesign/theme-neutral/fonts.css';
import '@astryxdesign/core/reset.css';
import '@astryxdesign/core/astryx.css';
import '@astryxdesign/theme-neutral/theme.css';
import {Theme} from '@astryxdesign/core/theme';
import {neutralTheme} from '@astryxdesign/theme-neutral/built';
import {InternationalizationProvider} from '@astryxdesign/core/i18n';
import ptBR from '@astryxdesign/core/locales/pt-BR.generated.js';
import App from './App.jsx';

createRoot(document.getElementById('root')).render(
  <Theme theme={neutralTheme}>
    <InternationalizationProvider locale="pt-BR" messages={{'pt-BR': ptBR}}>
      <App />
    </InternationalizationProvider>
  </Theme>,
);
