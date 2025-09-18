import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import PermissionInspector from '../../src/components/PermissionInspector'
import type { EffectivePermissionResult } from '../../src/types/workspace'

// Test data for different permission scenarios
const mockPermissionResults: Record<string, EffectivePermissionResult> = {
  writeAccess: {
    path: 'projects/app',
    status: 'write',
    matchedRule: {
      id: 'db-rule-5',
      path: 'projects',
      permission_type: 'write',
      rule_type: 'allow',
      description: 'Write access to projects',
      workspace_id: 3
    }
  },
  readAccess: {
    path: 'materials/docs',
    status: 'read',
    matchedRule: {
      id: 'db-rule-4',
      path: 'materials',
      permission_type: 'read',
      rule_type: 'allow',
      description: 'Read access to materials',
      workspace_id: 3
    }
  },
  deniedAccess: {
    path: 'projects/app',
    status: 'denied',
    matchedRule: {
      id: 'db-rule-8',
      path: 'projects',
      permission_type: 'read',
      rule_type: 'deny',
      description: 'Deny rule for projects',
      workspace_id: 2
    }
  },
  noAccess: {
    path: 'private/secret',
    status: 'none',
    matchedRule: null
  }
}

describe('PermissionInspector', () => {
  describe('Permission Status Mapping', () => {
    it('should display green RW indicator for write access', () => {
      render(
        <PermissionInspector
          path="projects/app"
          permissionResult={mockPermissionResults.writeAccess}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('RW')
      expect(indicator).toHaveClass('bg-green-500')
    })

    it('should display blue R indicator for read access', () => {
      render(
        <PermissionInspector
          path="materials/docs"
          permissionResult={mockPermissionResults.readAccess}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('R')
      expect(indicator).toHaveClass('bg-blue-500')
    })

    it('should display red X indicator for denied access', () => {
      render(
        <PermissionInspector
          path="projects/app"
          permissionResult={mockPermissionResults.deniedAccess}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('✕')
      expect(indicator).toHaveClass('bg-red-500')
    })

    it('should display gray ? indicator for no access rule', () => {
      render(
        <PermissionInspector
          path="private/secret"
          permissionResult={mockPermissionResults.noAccess}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('?')
      expect(indicator).toHaveClass('bg-gray-500')
    })
  })

  describe('Indicator Colors', () => {
    it('should use correct color classes for each status', () => {
      const testCases = [
        { result: mockPermissionResults.writeAccess, expectedClass: 'bg-green-500' },
        { result: mockPermissionResults.readAccess, expectedClass: 'bg-blue-500' },
        { result: mockPermissionResults.deniedAccess, expectedClass: 'bg-red-500' },
        { result: mockPermissionResults.noAccess, expectedClass: 'bg-gray-500' }
      ]

      testCases.forEach(({ result, expectedClass }) => {
        const { unmount } = render(
          <PermissionInspector
            path={result.path}
            permissionResult={result}
          />
        )

        const indicator = screen.getByRole('button')
        expect(indicator).toHaveClass(expectedClass)
        unmount()
      })
    })
  })

  describe('Tooltip Content', () => {
    it('should show correct tooltip title for each status', () => {
      const testCases = [
        { result: mockPermissionResults.writeAccess, expectedTitle: 'projects/app: write access' },
        { result: mockPermissionResults.readAccess, expectedTitle: 'materials/docs: read access' },
        { result: mockPermissionResults.deniedAccess, expectedTitle: 'projects/app: denied access' },
        { result: mockPermissionResults.noAccess, expectedTitle: 'private/secret: none access' }
      ]

      testCases.forEach(({ result, expectedTitle }) => {
        const { unmount } = render(
          <PermissionInspector
            path={result.path}
            permissionResult={result}
          />
        )

        const indicator = screen.getByRole('button')
        expect(indicator).toHaveAttribute('title', expectedTitle)
        unmount()
      })
    })
  })

  describe('Regression Tests', () => {
    it('should not break existing write permission display', () => {
      render(
        <PermissionInspector
          path="projects/app"
          permissionResult={mockPermissionResults.writeAccess}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('RW')
      expect(indicator).toHaveClass('bg-green-500', 'hover:bg-green-600')
    })

    it('should not break existing read permission display', () => {
      render(
        <PermissionInspector
          path="materials/docs"
          permissionResult={mockPermissionResults.readAccess}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('R')
      expect(indicator).toHaveClass('bg-blue-500', 'hover:bg-blue-600')
    })
  })

  describe('Edge Cases', () => {
    it('should handle unknown status gracefully', () => {
      const unknownResult: EffectivePermissionResult = {
        path: 'unknown/path',
        status: 'unknown' as any,
        matchedRule: null
      }

      render(
        <PermissionInspector
          path="unknown/path"
          permissionResult={unknownResult}
        />
      )

      const indicator = screen.getByRole('button')
      expect(indicator).toHaveTextContent('?')
      expect(indicator).toHaveClass('bg-gray-500')
    })
  })
})