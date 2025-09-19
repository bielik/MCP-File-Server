/**
 * Permission Inspector Component
 * Phase 3B: Advanced UI & Full Workspace Experience
 *
 * Shows detailed permission information on hover/click with matched rule explanations
 */

import React, { useState, useRef } from 'react'
import type { PermissionInspectorProps, EffectivePermissionResult } from '../types/workspace'

interface TooltipProps {
  result: EffectivePermissionResult
  isVisible: boolean
  position: { x: number; y: number }
}

function PermissionTooltip({ result, isVisible, position }: TooltipProps) {
  if (!isVisible) return null

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'write': return 'text-green-600 bg-green-50 border-green-200'
      case 'read': return 'text-blue-600 bg-blue-50 border-blue-200'
      case 'denied': return 'text-red-600 bg-red-50 border-red-200'
      case 'none': return 'text-red-600 bg-red-50 border-red-200'
      default: return 'text-gray-600 bg-gray-50 border-gray-200'
    }
  }

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'write':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536M9 13h6l2-2V7a2 2 0 00-2-2H9a2 2 0 00-2 2v4z" />
          </svg>
        )
      case 'read':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
        )
      case 'denied':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        )
      case 'none':
        return (
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L5.636 5.636" />
          </svg>
        )
      default:
        return null
    }
  }

  return (
    <div
      className="fixed z-50 max-w-sm bg-white border border-gray-200 rounded-lg shadow-lg p-3 pointer-events-none"
      style={{
        left: Math.min(position.x, window.innerWidth - 320),
        top: Math.max(10, position.y - 10),
      }}
    >
      <div className="space-y-2">
        {/* Status Header */}
        <div className={`flex items-center space-x-2 px-2 py-1 rounded border ${getStatusColor(result.status)}`}>
          {getStatusIcon(result.status)}
          <span className="font-semibold text-sm capitalize">
            {result.status === 'none' ? 'No Access' : `${result.status} Access`}
          </span>
        </div>

        {/* Path */}
        <div className="text-xs text-gray-600">
          <span className="font-medium">Path:</span> {result.path}
        </div>

        {/* Rule Information */}
        {result.matchedRule ? (
          <div className="text-xs space-y-1 border-t pt-2">
            <div>
              <span className="font-medium text-gray-700">Matched Rule:</span>
            </div>
            <div className="pl-2 space-y-1 text-gray-600">
              <div>ID: {result.matchedRule.id}</div>
              <div>Pattern: {result.matchedRule.path}</div>
              <div>Type: {result.matchedRule.rule_type} {result.matchedRule.permission_type}</div>
            </div>
          </div>
        ) : (
          <div className="text-xs text-gray-500 border-t pt-2">
            No matching rule (default deny)
          </div>
        )}

        <div className="text-xs text-gray-400 border-t pt-1">
          Click for detailed view
        </div>
      </div>
    </div>
  )
}

interface DetailedModalProps {
  result: EffectivePermissionResult
  isOpen: boolean
  onClose: () => void
}

function DetailedPermissionModal({ result, isOpen, onClose }: DetailedModalProps) {
  const [copied, setCopied] = useState(false)

  const copyRuleId = async () => {
    if (result.matchedRule?.id) {
      try {
        await navigator.clipboard.writeText(result.matchedRule.id)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (error) {
        console.error('Failed to copy rule ID:', error)
      }
    }
  }

  if (!isOpen) return null

  const getStatusDetails = (status: string) => {
    switch (status) {
      case 'write':
        return {
          title: 'Write Access',
          description: 'Full read and write permissions to this path and its contents',
          color: 'bg-green-100 text-green-800',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536M9 13h6l2-2V7a2 2 0 00-2-2H9a2 2 0 00-2 2v4z" />
            </svg>
          )
        }
      case 'read':
        return {
          title: 'Read Access',
          description: 'Can view and read files, but cannot modify or create new files',
          color: 'bg-blue-100 text-blue-800',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
            </svg>
          )
        }
      case 'denied':
        return {
          title: 'Access Denied',
          description: 'Explicitly denied by permission rule - cannot read, write, or access this path',
          color: 'bg-red-100 text-red-800',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          )
        }
      case 'none':
        return {
          title: 'No Access',
          description: 'Access denied - cannot read, write, or access this path',
          color: 'bg-red-100 text-red-800',
          icon: (
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728L5.636 5.636m12.728 12.728L5.636 5.636" />
            </svg>
          )
        }
      default:
        return {
          title: 'Unknown',
          description: 'Permission status unknown',
          color: 'bg-gray-100 text-gray-800',
          icon: null
        }
    }
  }

  const statusDetails = getStatusDetails(result.status)

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="flex items-center justify-between p-6 border-b">
          <h2 className="text-xl font-semibold text-gray-900">Permission Details</h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600 transition-colors"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-6 space-y-6">
          {/* Path Information */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">File Path</h3>
            <div className="bg-gray-50 p-3 rounded-lg">
              <code className="text-sm font-mono text-gray-800">{result.path}</code>
            </div>
          </div>

          {/* Permission Status */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Access Level</h3>
            <div className={`flex items-center space-x-3 p-4 rounded-lg ${statusDetails.color}`}>
              {statusDetails.icon}
              <div>
                <div className="font-semibold">{statusDetails.title}</div>
                <div className="text-sm opacity-90">{statusDetails.description}</div>
              </div>
            </div>
          </div>

          {/* Matched Rule Details */}
          {result.matchedRule ? (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">Matched Rule</h3>
              <div className="bg-gray-50 p-4 rounded-lg space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Rule ID</label>
                    <div className="flex items-center space-x-2">
                      <code className="text-sm bg-white px-2 py-1 rounded border">{result.matchedRule.id}</code>
                      <button
                        onClick={copyRuleId}
                        className="p-1 text-gray-400 hover:text-gray-600 transition-colors"
                        title="Copy rule ID"
                      >
                        {copied ? (
                          <svg className="w-4 h-4 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                          </svg>
                        )}
                      </button>
                    </div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Workspace ID</label>
                    <div className="text-sm bg-white px-2 py-1 rounded border">{result.matchedRule.workspace_id}</div>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Rule Pattern</label>
                    <code className="text-sm bg-white px-2 py-1 rounded border block">{result.matchedRule.path}</code>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Rule Type</label>
                    <div className="text-sm">
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        result.matchedRule.rule_type === 'allow' ? 'bg-green-100 text-green-800' : 'bg-red-100 text-red-800'
                      }`}>
                        {result.matchedRule.rule_type}
                      </span>
                      <span className="mx-2 text-gray-500">→</span>
                      <span className={`px-2 py-1 rounded text-xs font-medium ${
                        result.matchedRule.permission_type === 'write' ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800'
                      }`}>
                        {result.matchedRule.permission_type}
                      </span>
                    </div>
                  </div>
                </div>

                {result.matchedRule.description && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
                    <div className="text-sm text-gray-600 bg-white px-3 py-2 rounded border">
                      {result.matchedRule.description}
                    </div>
                  </div>
                )}

                {result.matchedRule.precedence_reason && (
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">Why This Rule Matched</label>
                    <div className="text-sm text-gray-600 bg-blue-50 px-3 py-2 rounded border border-blue-200">
                      {result.matchedRule.precedence_reason}
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            <div>
              <h3 className="text-lg font-medium text-gray-900 mb-3">No Matching Rule</h3>
              <div className="bg-red-50 p-4 rounded-lg border border-red-200">
                <div className="text-red-800">
                  <div className="font-medium mb-1">Default Deny Applied</div>
                  <div className="text-sm">
                    No permission rules match this path. The system defaults to denying access for security.
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* Precedence Information */}
          <div>
            <h3 className="text-lg font-medium text-gray-900 mb-3">Permission Precedence Rules</h3>
            <div className="bg-blue-50 p-4 rounded-lg border border-blue-200">
              <ol className="text-sm text-blue-900 space-y-1 list-decimal list-inside">
                <li><strong>Specificity:</strong> More specific paths override general ones</li>
                <li><strong>Deny Wins:</strong> Deny rules override allow rules at the same specificity</li>
                <li><strong>Write Implies Read:</strong> Write permission automatically grants read access</li>
                <li><strong>Default Deny:</strong> Access denied if no rules match</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Footer */}
        <div className="flex justify-end p-6 border-t bg-gray-50">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            Close
          </button>
        </div>
      </div>
    </div>
  )
}

export default function PermissionInspector({ path, permissionResult, onClose }: PermissionInspectorProps) {
  const [showTooltip, setShowTooltip] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [mousePosition, setMousePosition] = useState({ x: 0, y: 0 })
  const containerRef = useRef<HTMLDivElement>(null)

  const handleMouseEnter = (e: React.MouseEvent) => {
    setMousePosition({ x: e.clientX, y: e.clientY })
    setShowTooltip(true)
  }

  const handleMouseLeave = () => {
    setShowTooltip(false)
  }

  const handleClick = () => {
    setShowModal(true)
    setShowTooltip(false)
  }

  const handleCloseModal = () => {
    setShowModal(false)
    if (onClose) onClose()
  }

  const getIndicatorColor = (status: string) => {
    switch (status) {
      case 'write': return 'bg-green-500 hover:bg-green-600'
      case 'read': return 'bg-blue-500 hover:bg-blue-600'
      case 'denied': return 'bg-red-500 hover:bg-red-600'
      case 'none': return 'bg-gray-500 hover:bg-gray-600'
      default: return 'bg-gray-500 hover:bg-gray-600'
    }
  }

  const getIndicatorText = (status: string) => {
    switch (status) {
      case 'write': return 'RW'
      case 'read': return 'R'
      case 'denied': return '✕'
      case 'none': return '?'
      default: return '?'
    }
  }

  return (
    <>
      <div
        ref={containerRef}
        className={`inline-block w-6 h-6 rounded text-white text-xs font-bold cursor-pointer transition-colors ${getIndicatorColor(permissionResult.status)}`}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
        onClick={handleClick}
        title={`${path}: ${permissionResult.status} access`}
      >
        <div className="flex items-center justify-center h-full">
          {getIndicatorText(permissionResult.status)}
        </div>
      </div>

      <PermissionTooltip
        result={permissionResult}
        isVisible={showTooltip}
        position={mousePosition}
      />

      <DetailedPermissionModal
        result={permissionResult}
        isOpen={showModal}
        onClose={handleCloseModal}
      />
    </>
  )
}