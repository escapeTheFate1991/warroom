/**
 * Safe Markdown Component
 * 
 * Wraps ReactMarkdown with DOMPurify sanitization to prevent XSS attacks.
 * Should be used for all user-generated or untrusted markdown content.
 */
import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import DOMPurify from 'dompurify';

interface SafeMarkdownProps {
  children: string;
  className?: string;
  remarkPlugins?: any[];
  allowedTags?: string[];
}

// Default allowed HTML tags for markdown content
const DEFAULT_ALLOWED_TAGS = [
  'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
  'p', 'br', 'hr',
  'strong', 'b', 'em', 'i', 'u', 's',
  'ul', 'ol', 'li',
  'blockquote', 'pre', 'code',
  'a', 'img',
  'table', 'thead', 'tbody', 'tr', 'th', 'td',
];

// Allowed attributes for specific tags
const DEFAULT_ALLOWED_ATTRIBUTES = {
  a: ['href', 'title'],
  img: ['src', 'alt', 'title'],
  '*': ['className', 'class'] // Allow CSS classes
};

export function SafeMarkdown({ 
  children, 
  className, 
  remarkPlugins = [remarkGfm], 
  allowedTags = DEFAULT_ALLOWED_TAGS 
}: SafeMarkdownProps) {
  // Sanitize the markdown content before rendering
  const sanitizedContent = React.useMemo(() => {
    if (!children) return '';
    
    // First pass: basic HTML sanitization
    const cleanHtml = DOMPurify.sanitize(children, {
      ALLOWED_TAGS: allowedTags,
      ALLOWED_ATTR: ['href', 'title', 'src', 'alt', 'className', 'class'],
      FORBID_TAGS: ['script', 'style', 'iframe', 'object', 'embed'],
      FORBID_ATTR: ['onerror', 'onload', 'onclick', 'onmouseover', 'onfocus', 'onblur']
    });
    
    return cleanHtml;
  }, [children, allowedTags]);

  return (
    <ReactMarkdown 
      className={className}
      remarkPlugins={remarkPlugins}
      components={{
        // Sanitize any additional HTML that might be generated
        // eslint-disable-next-line @typescript-eslint/no-unused-vars
        html: ({ node, ...props }) => {
          // Strip any raw HTML to be safe
          return null;
        },
        // Ensure links open safely
        a: ({ href, children, ...props }) => (
          <a
            href={href}
            target={href?.startsWith('http') ? '_blank' : undefined}
            rel={href?.startsWith('http') ? 'noopener noreferrer' : undefined}
            {...props}
          >
            {children}
          </a>
        ),
        // Sanitize image sources
        img: ({ src, alt, ...props }) => {
          // Only allow safe image sources
          const safeSrc = src?.match(/^(https?:\/\/|data:image\/)/i) ? src : '';
          return safeSrc ? <img src={safeSrc} alt={alt} {...props} /> : null;
        }
      }}
    >
      {sanitizedContent}
    </ReactMarkdown>
  );
}

export default SafeMarkdown;