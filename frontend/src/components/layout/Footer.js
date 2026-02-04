import React from 'react';
import {
  Mail,
  ExternalLink,
  ChevronRight
} from 'lucide-react';
import { useIsMobile, useIsTablet } from '../../hooks/useMediaQuery';

const Footer = () => {
  const isMobile = useIsMobile();
  const isTablet = useIsTablet();
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

  // Natural visual appearance - touch target handled by .touch-target-link class
  const linkStyle = {
    color: 'var(--text-light)',
    textDecoration: 'none',
    fontSize: '0.9375rem',
    display: 'flex',
    alignItems: 'center',
    gap: '0.5rem',
    marginBottom: '0.75rem',
    transition: 'color 0.2s ease',
    cursor: 'pointer',
    lineHeight: '1.5',
    paddingLeft: '0.25rem',
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
            gridTemplateColumns: isMobile ? '1fr' : isTablet ? 'repeat(2, 1fr)' : 'repeat(3, 1fr)',
            gap: isMobile ? '3rem' : '4rem',
            alignItems: 'start'
          }}>
            {/* About Section */}
            <div>
              <h3 style={{
                fontSize: '1.25rem',
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
                <div style={sectionTitleStyle}>Funded by</div>
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
                display: isMobile ? 'none' : 'block'
              }}></div>
              <div style={sectionTitleStyle}>Resources</div>
              <div>
                <a
                  href="http://aggregator.localhost/api/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="touch-target-link"
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  API Documentation
                </a>
                <a
                  href="/changelog"
                  className="touch-target-link"
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  Changelog
                </a>
                <a
                  href="/about"
                  className="touch-target-link"
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  About
                </a>
                <a
                  href="https://github.com/gfbio"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="touch-target-link"
                  style={linkStyle}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ChevronRight size={14} />
                  GitHub
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
                display: isMobile ? 'none' : 'block'
              }}></div>
              <div style={sectionTitleStyle}>Contact & Support</div>
              <p style={{
                fontSize: '0.9375rem',
                color: 'var(--text-light)',
                marginBottom: '1.25rem',
                lineHeight: '1.6'
              }}>
                Need help with data integration, API usage, or platform features?
              </p>
              {/* Contact links grouped together */}
              <div style={{ marginBottom: '1.5rem' }}>
                <a
                  href="mailto:info@gfbio.org"
                  className="touch-target-link"
                  style={{
                    ...linkStyle,
                    marginBottom: '0.5rem'
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <Mail size={16} />
                  info@gfbio.org
                </a>
                <a
                  href="https://www.gfbio.org"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="touch-target-link"
                  style={{
                    ...linkStyle,
                    marginBottom: '0'
                  }}
                  onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                  onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                  <ExternalLink size={16} />
                  www.gfbio.org
                </a>
              </div>
              {/* Organization Address */}
              <div style={{
                marginTop: '1.5rem',
                paddingTop: '1.25rem',
                borderTop: '1px solid var(--border)'
              }}>
                <div style={{
                  color: 'var(--text)',
                  fontWeight: '600',
                  fontSize: '0.875rem',
                  marginBottom: '0.5rem'
                }}>
                  GFBio e.V.
                </div>
                <div style={{
                  fontSize: '0.8125rem',
                  color: 'var(--text-light)',
                  lineHeight: '1.6'
                }}>
                  Unicom 2, Haus 2-4<br/>
                  Mary-Somerville-Str. 2<br/>
                  28359 Bremen, Germany
                </div>
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
              gap: isMobile ? '0.5rem' : '1.5rem',
              alignItems: 'center',
              flexWrap: 'wrap'
            }}>
              <a
                href="https://www.gfbio.org/terms-of-use/"
                target="_blank"
                rel="noopener noreferrer"
                className="touch-target-link"
                style={{
                  color: 'var(--text-light)',
                  textDecoration: 'none',
                  fontSize: '0.8125rem',
                  transition: 'color 0.2s ease',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontWeight: '500',
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                Terms of Use
              </a>
              <span style={{ color: 'var(--border)', fontSize: '0.75rem', display: isMobile ? 'none' : 'inline' }}>•</span>
              <a
                href="https://www.gfbio.org/legal-notice/"
                target="_blank"
                rel="noopener noreferrer"
                className="touch-target-link"
                style={{
                  color: 'var(--text-light)',
                  textDecoration: 'none',
                  fontSize: '0.8125rem',
                  transition: 'color 0.2s ease',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontWeight: '500',
                }}
                onMouseEnter={e => e.currentTarget.style.color = 'var(--primary)'}
                onMouseLeave={e => e.currentTarget.style.color = 'var(--text-light)'}>
                Legal Notice
              </a>
              <span style={{ color: 'var(--border)', fontSize: '0.75rem', display: isMobile ? 'none' : 'inline' }}>•</span>
              <a
                href="https://www.gfbio.org/privacy-policy/"
                target="_blank"
                rel="noopener noreferrer"
                className="touch-target-link"
                style={{
                  color: 'var(--text-light)',
                  textDecoration: 'none',
                  fontSize: '0.8125rem',
                  transition: 'color 0.2s ease',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '0.25rem',
                  fontWeight: '500',
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
