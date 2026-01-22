/**
 * MSW Server Setup
 *
 * Creates the MSW server for testing API calls.
 */

import { setupServer } from 'msw/node';
import { handlers } from './api';

// Create the MSW server with default handlers
export const server = setupServer(...handlers);

export default server;
