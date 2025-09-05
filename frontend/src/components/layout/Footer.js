import React from 'react';
import { 
  Github,
  Mail,
  ExternalLink,
  BookOpen,
  HelpCircle,
  ChevronRight
} from 'lucide-react';

const Footer = () => {
  const currentYear = new Date().getFullYear();

  const footerMainStyle = {
    backgroundColor: 'var(--card-bg)',
    backgroundImage: 'linear-gradient(to bottom, var(--card-bg), var(--subtle-bg, var(--card-bg)))',
    borderTop: '1px solid var(--border)',
    position: 'relative'
  };

  const footerBottomStyle = {
    backgroundColor: 'var(--subtle-bg, var(--card-bg))',
    borderTop: '1px solid var(--border)',
    color: 'var(--text-light)'
  };

  const containerStyle = {
    padding: '3.5rem 1rem 3rem',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%'
  };

  const bottomContainerStyle = {
    padding: '1.5rem 1rem',
    maxWidth: '1200px',
    margin: '0 auto',
    width: '100%'
  };

  const sectionTitleStyle = {
    fontSize: '1rem',
    fontWeight: '700',
    marginBottom: '1rem',
    color: 'var(--text)',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    textTransform: 'uppercase',
    letterSpacing: '0.05em'
  };

  const linkStyle = {
    color: 'var(--text-light)',
    textDecoration: 'none',
    fontSize: '0.9375rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.75rem',
    transition: 'all 0.2s ease',
    cursor: 'pointer',
    lineHeight: '1.5',
    paddingLeft: '0.25rem'
  };

  return (
    <footer style={{ 
      marginTop: 'auto'
    }}>
      {/* Main Footer Section */}
      <div style={footerMainStyle}>
        <div style={containerStyle}>
          <div style={{ 
            display: 'grid', 
            gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
            gap: window.innerWidth <= 768 ? '3rem' : '4rem',
            alignItems: 'start'
          }}>
            {/* About Section */}
            <div>
              <h3 style={{ 
                fontSize: '1.5rem', 
                marginBottom: '1.25rem',
                fontWeight: '700',
                color: 'var(--text)',
                letterSpacing: '-0.025em',
                lineHeight: '1.2'
              }}>
                GFBio DPM 
              </h3>
              <p style={{ 
                fontSize: '0.9375rem', 
                lineHeight: '1.7',
                color: 'var(--text-light)',
                marginBottom: '2rem',
                maxWidth: '280px'
              }}>
                A biological data registry facilitating discovery, access, and 
                integration of biological and environmental research data from the German Federation for Biological Data.
              </p>
              <div style={{ 
                fontSize: '0.8125rem',
                color: 'var(--text-light)',
                marginTop: '2rem'
              }}>
                <div style={{ marginBottom: '0.75rem', color: 'var(--text)', fontWeight: '600' }}>Funded by</div>
                <div style={{
                  backgroundColor: 'var(--subtle-bg, var(--card-bg))',
                  padding: '0.75rem 1.25rem',
                  borderRadius: '0.5rem',
                  display: 'inline-block',
                  border: '1px solid var(--border)',
                  boxShadow: '0 1px 3px rgba(0, 0, 0, 0.05)'
                }}>
                  <div style={{ color: 'var(--text)', fontWeight: '700', fontSize: '0.9375rem' }}>DFG</div>
                  <div style={{ color: 'var(--text-light)', fontSize: '0.6875rem', marginTop: '0.125rem' }}>German Research Foundation</div>
                </div>
              </div>
            </div>

            {/* Resources Section */}
            <div style={{ position: 'relative' }}>
              <div style={{
                position: 'absolute',
                left: '-2rem',
                top: '0',
                bottom: '0',
                width: '1px',
                background: 'linear-gradient(to bottom, transparent, var(--border), transparent)',
                display: window.innerWidth > 768 ? 'block' : 'none'
              }}></div>
              <div style={sectionTitleStyle}>
                <BookOpen size={16} />
                <span>Resources</span>
              </div>
              <div>
                <a 
                  href="/documentation" 
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  API Documentation
                </a>
                <a 
                  href="/training" 
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  Training Materials
                </a>
                <a 
                  href="/faq" 
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  FAQ's
                </a>
                <a 
                  href="/changelog" 
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  Changelog
                </a>
                <a 
                  href="/about" 
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  About
                </a>
              </div>
            </div>

            {/* Support */}
            <div style={{ position: 'relative' }}>
              <div style={{
                position: 'absolute',
                left: '-2rem',
                top: '0',
                bottom: '0',
                width: '1px',
                background: 'linear-gradient(to bottom, transparent, var(--border), transparent)',
                display: window.innerWidth > 768 ? 'block' : 'none'
              }}></div>
              <div style={sectionTitleStyle}>
                <HelpCircle size={16} />
                <span>Contact & Support</span>
              </div>
              <p style={{ 
                fontSize: '0.9375rem',
                color: 'var(--text-light)',
                marginBottom: '1.5rem',
                lineHeight: '1.6'
              }}>
                Need help with data integration, API usage, or platform features?
              </p>
              <a 
                href="mailto:support@gfbio.org"
                style={{
                  ...linkStyle,
                  display: 'inline-flex',
                  marginBottom: '1.5rem',
                  color: 'var(--primary)',
                  fontWeight: '600',
                  padding: '0.5rem 0.75rem',
                  borderRadius: '0.375rem',
                  backgroundColor: 'rgba(var(--primary-rgb, 59, 130, 246), 0.08)',
                  border: '1px solid rgba(var(--primary-rgb, 59, 130, 246), 0.15)'
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.backgroundColor = 'rgba(var(--primary-rgb, 59, 130, 246), 0.12)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.backgroundColor = 'rgba(var(--primary-rgb, 59, 130, 246), 0.08)';
                  e.currentTarget.style.transform = 'translateY(0)';
                }}>
                <Mail size={16} />
                support@gfbio.org
              </a>
              <div style={{
                display: 'flex',
                gap: '0.75rem',
                marginTop: '0'
              }}>
                <a 
                  href="https://github.com/gfbio"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: 'var(--text-light)',
                    transition: 'all 0.2s ease',
                    padding: '0.5rem',
                    borderRadius: '0.375rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid var(--border)'
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.color = 'var(--primary)';
                    e.currentTarget.style.backgroundColor = 'var(--subtle-bg, var(--card-bg))';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.color = 'var(--text-light)';
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                  aria-label="GitHub">
                  <Github size={18} />
                </a>
                <a 
                  href="https://www.gfbio.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    color: 'var(--text-light)',
                    transition: 'all 0.2s ease',
                    padding: '0.5rem',
                    borderRadius: '0.375rem',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    border: '1px solid var(--border)'
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.color = 'var(--primary)';
                    e.currentTarget.style.backgroundColor = 'var(--subtle-bg, var(--card-bg))';
                    e.currentTarget.style.transform = 'translateY(-2px)';
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.color = 'var(--text-light)';
                    e.currentTarget.style.backgroundColor = 'transparent';
                    e.currentTarget.style.transform = 'translateY(0)';
                  }}
                  aria-label="GFBio Website">
                  <ExternalLink size={18} />
                </a>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Bottom Bar */}
      <div style={footerBottomStyle}>
        <div style={bottomContainerStyle}>
          <div style={{
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: '1rem'
          }}>
            {/* Legal Links */}
            <div style={{
              display: 'flex',
              gap: '2rem',
              alignItems: 'center',
              flexWrap: 'wrap'
            }}>
              <a 
                href="/terms" 
                style={{
                  color: 'var(--text-light)',
                  textDecoration: 'none',
                  fontSize: '0.8125rem',
                  transition: 'color 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontWeight: '500'
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                Terms of Use
              </a>
              <span style={{ color: 'var(--border)', fontSize: '0.75rem' }}>•</span>
              <a 
                href="/legal" 
                style={{
                  color: 'var(--text-light)',
                  textDecoration: 'none',
                  fontSize: '0.8125rem',
                  transition: 'color 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontWeight: '500'
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                Legal Notice
              </a>
              <span style={{ color: 'var(--border)', fontSize: '0.75rem' }}>•</span>
              <a 
                href="/privacy" 
                style={{
                  color: 'var(--text-light)',
                  textDecoration: 'none',
                  fontSize: '0.8125rem',
                  transition: 'color 0.2s ease',
                  display: 'flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontWeight: '500'
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                Privacy Policy
              </a>
            </div>

            {/* Copyright */}
            <div style={{ 
              fontSize: '0.8125rem',
              color: 'var(--text-light)',
              fontWeight: '500'
            }}>
              © {currentYear} GFBio e.V. All rights reserved.
            </div>
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;
