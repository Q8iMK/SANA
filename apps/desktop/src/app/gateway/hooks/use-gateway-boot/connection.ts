import type { HermesConnection } from '@/global'

/** Registry identity whose runtimes died with the primary connection. */
export function primaryRuntimeConnectionId(connection: Pick<HermesConnection, 'connectionId' | 'mode'>): null | string {
  const connectionId = connection.connectionId?.trim()

  if (connectionId) {
    return connectionId
  }

  return connection.mode === 'local' ? 'local' : null
}
