import React from 'react';
import { render, screen } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import { sanitizeArtifactHtml } from '../utils/sanitizer';
import SandboxedArtifactViewer from '../components/SandboxedArtifactViewer';

describe('Frontend Security & Sanitization Suite', () => {
  it('strips <script> tags and inline script execution', () => {
    const dirty = '<div><h1>Title</h1><script>alert("xss_test")</script><p>Body text</p></div>';
    const clean = sanitizeArtifactHtml(dirty);
    expect(clean).not.toContain('<script>');
    expect(clean).not.toContain('alert("xss_test")');
    expect(clean).toContain('<h1>Title</h1>');
    expect(clean).toContain('<p>Body text</p>');
  });

  it('strips inline event handler attributes (onerror, onclick, onload)', () => {
    const dirty = '<img src="invalid.png" onerror="alert(\'img_xss\')" /><a href="#" onclick="alert(\'click_xss\')">Click</a>';
    const clean = sanitizeArtifactHtml(dirty);
    expect(clean).not.toContain('onerror');
    expect(clean).not.toContain('onclick');
    expect(clean).not.toContain('alert');
  });

  it('blocks dangerous javascript: and data: URL schemes', () => {
    const dirty = '<a href="javascript:alert(\'js_uri\')">Malicious Link</a><iframe src="javascript:alert(1)"></iframe>';
    const clean = sanitizeArtifactHtml(dirty);
    expect(clean).not.toContain('javascript:alert');
    expect(clean).not.toContain('<iframe');
  });

  it('sanitizes SVG-based XSS payloads', () => {
    const dirty = '<svg onload="alert(\'svg_xss\')"><rect width="100" height="100"/></svg>';
    const clean = sanitizeArtifactHtml(dirty);
    expect(clean).not.toContain('onload');
    expect(clean).not.toContain('alert(\'svg_xss\')');
  });

  it('sanitizes rendered Markdown HTML containing embedded malicious tags', () => {
    const rawMarkdownHtml = '<h1>Ship 30 Essay</h1><script>window.location="http://attacker.com"</script><p>Safe content</p>';
    const clean = sanitizeArtifactHtml(rawMarkdownHtml);
    expect(clean).not.toContain('<script>');
    expect(clean).not.toContain('attacker.com');
    expect(clean).toContain('<h1>Ship 30 Essay</h1>');
    expect(clean).toContain('<p>Safe content</p>');
  });

  it('verifies that SandboxedArtifactViewer iframe preserves strict sandbox="" attribute', () => {
    const artifact = {
      title: 'Security Evaluation Essay',
      format: 'html',
      content: '<h1>Security Test</h1><p>Test content</p>',
      citations: []
    };

    render(<SandboxedArtifactViewer artifact={artifact} onClose={() => {}} />);
    
    const iframe = screen.getByTitle('Security Evaluation Essay');
    expect(iframe).toBeTruthy();
    expect(iframe).toHaveAttribute('sandbox', '');
    
    const sandboxValue = iframe.getAttribute('sandbox');
    expect(sandboxValue).not.toContain('allow-scripts');
    expect(sandboxValue).not.toContain('allow-same-origin');
    expect(sandboxValue).not.toContain('allow-forms');
    expect(sandboxValue).not.toContain('allow-popups');
    expect(sandboxValue).not.toContain('allow-top-navigation');
  });
});
