import React from 'react';
import clsx from 'clsx';

interface HeaderProps {
  children?: React.ReactNode;
  className?: string;
}

export function Header({ children, className }: HeaderProps) {
  return (
    <header className={clsx('flex items-center', className)}>
      {children}
    </header>
  );
}