import React from 'react';
import { Lock, Edit3, Bot } from 'lucide-react';
import clsx from 'clsx';

type PermissionType = 'read-only' | 'read-write' | 'agent-controlled';

interface PermissionBadgeProps {
  permission: PermissionType;
  size?: 'sm' | 'md' | 'lg';
  showIcon?: boolean;
  showText?: boolean;
  className?: string;
}

const permissionConfig = {
  'read-only': {
    icon: Lock,
    label: 'Read Only',
    shortLabel: 'RO',
    color: 'text-warning-700',
    bgColor: 'bg-warning-100',
    borderColor: 'border-warning-200',
    description: 'Reference materials - cannot be modified',
  },
  'read-write': {
    icon: Edit3,
    label: 'Read Write',
    shortLabel: 'RW',
    color: 'text-success-700',
    bgColor: 'bg-success-100',
    borderColor: 'border-success-200',
    description: 'Editable documents for collaboration',
  },
  'agent-controlled': {
    icon: Bot,
    label: 'Agent Controlled',
    shortLabel: 'AI',
    color: 'text-primary-700',
    bgColor: 'bg-primary-100',
    borderColor: 'border-primary-200',
    description: 'AI agents can create and manage files',
  },
};

const sizeConfig = {
  sm: {
    padding: 'px-1.5 py-0.5',
    text: 'text-xs',
    iconSize: 12,
  },
  md: {
    padding: 'px-2 py-1',
    text: 'text-sm',
    iconSize: 14,
  },
  lg: {
    padding: 'px-3 py-1.5',
    text: 'text-base',
    iconSize: 16,
  },
};

export function PermissionBadge({
  permission,
  size = 'md',
  showIcon = true,
  showText = true,
  className,
}: PermissionBadgeProps) {
  const config = permissionConfig[permission];
  const sizeProps = sizeConfig[size];
  const IconComponent = config.icon;

  return (
    <div
      className={clsx(
        'inline-flex items-center rounded-full border font-medium',
        config.color,
        config.bgColor,
        config.borderColor,
        sizeProps.padding,
        sizeProps.text,
        className
      )}
      title={`${config.label}: ${config.description}`}
    >
      {showIcon && (
        <IconComponent
          size={sizeProps.iconSize}
          className={clsx('flex-shrink-0', showText && 'mr-1')}
        />
      )}
      {showText && (
        <span className="truncate">
          {size === 'sm' ? config.shortLabel : config.label}
        </span>
      )}
    </div>
  );
}

// Utility component for permission status in different contexts
export function PermissionIndicator({
  permission,
  variant = 'badge',
  className,
}: {
  permission: PermissionType;
  variant?: 'badge' | 'dot' | 'icon';
  className?: string;
}) {
  const config = permissionConfig[permission];
  
  if (variant === 'dot') {
    return (
      <div
        className={clsx(
          'w-2 h-2 rounded-full flex-shrink-0',
          config.bgColor.replace('bg-', 'bg-').replace('-100', '-500'),
          className
        )}
        title={`${config.label}: ${config.description}`}
      />
    );
  }
  
  if (variant === 'icon') {
    const IconComponent = config.icon;
    return (
      <IconComponent
        size={16}
        className={clsx(config.color, className)}
      />
    );
  }
  
  return (
    <PermissionBadge
      permission={permission}
      size="sm"
      className={className}
    />
  );
}

// Permission selector component for forms
export function PermissionSelector({
  value,
  onChange,
  disabled = false,
  className,
}: {
  value: PermissionType;
  onChange: (permission: PermissionType) => void;
  disabled?: boolean;
  className?: string;
}) {
  return (
    <div className={clsx('space-y-2', className)}>
      <label className="block text-sm font-medium text-gray-700">
        Permission Level
      </label>
      <div className="space-y-2">
        {(Object.keys(permissionConfig) as PermissionType[]).map((permission) => {
          const config = permissionConfig[permission];
          const IconComponent = config.icon;
          
          return (
            <label
              key={permission}
              className={clsx(
                'flex items-center p-3 rounded-lg border-2 cursor-pointer transition-all',
                value === permission
                  ? `${config.borderColor} ${config.bgColor}`
                  : 'border-gray-200 hover:border-gray-300 hover:bg-gray-50',
                disabled && 'opacity-50 cursor-not-allowed'
              )}
            >
              <input
                type="radio"
                name="permission"
                value={permission}
                checked={value === permission}
                onChange={(e) => onChange(e.target.value as PermissionType)}
                disabled={disabled}
                className="sr-only"
              />
              <IconComponent
                size={20}
                className={clsx(
                  'mr-3 flex-shrink-0',
                  value === permission ? config.color : 'text-gray-400'
                )}
              />
              <div className="flex-1">
                <div className={clsx(
                  'font-medium',
                  value === permission ? config.color : 'text-gray-900'
                )}>
                  {config.label}
                </div>
                <div className="text-sm text-gray-500">
                  {config.description}
                </div>
              </div>
            </label>
          );
        })}
      </div>
    </div>
  );
}