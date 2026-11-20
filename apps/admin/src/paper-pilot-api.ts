import { decodePilotReadEnvelope } from './paper-pilot-data';
import { PilotReadError, type PilotReader } from './PaperPilotWorkspace';
import { staffRequest } from './staff-api';

const query = '?requestSchemaVersion=v1';
const sessions = '/api/admin/pilot/sessions';

export function paperPilotReader(loginId: string): PilotReader {
  async function read(path: string, signal: AbortSignal): Promise<unknown> {
    const response = await staffRequest(path + query, undefined, loginId, 5000, signal);
    if (response.status !== 200) throw new PilotReadError(response.status);
    return response.json();
  }

  return {
    async list(signal) {
      return decodePilotReadEnvelope(await read(sessions, signal), 'sessions');
    },
    session(sessionId, signal) {
      return read('/api/admin/sessions/' + encodeURIComponent(sessionId), signal);
    },
    async events(sessionId, signal) {
      const path = sessions + '/' + encodeURIComponent(sessionId) + '/events';
      return decodePilotReadEnvelope(await read(path, signal), 'events', sessionId);
    },
  };
}
