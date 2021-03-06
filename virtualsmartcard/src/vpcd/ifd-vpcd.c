#include <stdio.h>
#include <stdlib.h>

#include <string.h>

/* The default configuration for vpcd provides a IFD-handler conforming to
 * version 2 of the IFDHandler API with adjustable port by ChannelID in
 * reader.conf. If you want vpcd to conform to version 3, you must...
 * 1. have a pcscd of r5294 and later (see but #312749 on
 *    https://alioth.debian.org/projects/pcsclite/ )
 * 2. remove the line "DEVICENAME   /dev/null" from the provided reader.conf
 * 3. not define IFDHANDLERv2 (e.g. remove the following line) */
#define IFDHANDLERv2

#include <ifdhandler.h>

#include <debuglog.h>

#include "vpcd.h"

RESPONSECODE
IFDHCreateChannel (DWORD Lun, DWORD Channel)
{
    if (vicc_init(Channel) < 0) {
        Log1(PCSC_LOG_ERROR, "Could not initialize connection to virtual ICC");
        return IFD_COMMUNICATION_ERROR;
    }
    Log2(PCSC_LOG_INFO, "Waiting for virtual ICC on port %hu", (unsigned short) Channel);

    return IFD_SUCCESS;
}

#ifndef IFDHANDLERv2
RESPONSECODE
IFDHCreateChannelByName (DWORD Lun, LPSTR DeviceName)
{
    Log3(PCSC_LOG_INFO, "Not opening %s. Using default port %hu", DeviceName, VPCDPORT);
    return IFDHCreateChannel (Lun, VPCDPORT);
}

RESPONSECODE
IFDHControl (DWORD Lun, DWORD dwControlCode, PUCHAR TxBuffer, DWORD TxLength,
        PUCHAR RxBuffer, DWORD RxLength, LPDWORD pdwBytesReturned)
{
    Log9(PCSC_LOG_DEBUG, "IFDHControl not supported (Lun=%u ControlCode=%u TxBuffer=%p TxLength=%u RxBuffer=%p RxLength=%u pBytesReturned=%p)%s",
            (unsigned int) Lun, (unsigned int) dwControlCode,
            (unsigned char *) TxBuffer, (unsigned int) TxLength,
            (unsigned char *) RxBuffer, (unsigned int) RxLength,
            (unsigned int *) pdwBytesReturned, "");
    return IFD_ERROR_NOT_SUPPORTED;
}
#else
RESPONSECODE
IFDHControl(DWORD Lun, PUCHAR TxBuffer, DWORD TxLength, PUCHAR RxBuffer,
        PDWORD RxLength)
{
    Log9(PCSC_LOG_DEBUG, "IFDHControl not supported (Lun=%u%s TxBuffer=%p TxLength=%u RxBuffer=%p RxLength=%u%s)%s",
            (unsigned int) Lun, "",
            (unsigned char *) TxBuffer, (unsigned int) TxLength,
            (unsigned char *) RxBuffer, (unsigned int) RxLength,
            "", "");
    return IFD_ERROR_NOT_SUPPORTED;
}
#endif

RESPONSECODE
IFDHCloseChannel (DWORD Lun)
{
    RESPONSECODE r = vicc_eject();
    if (vicc_exit() < 0) {
        Log1(PCSC_LOG_ERROR, "Could not close connection to virtual ICC");
        return IFD_COMMUNICATION_ERROR;
    }

    return r;
}

RESPONSECODE
IFDHGetCapabilities (DWORD Lun, DWORD Tag, PDWORD Length, PUCHAR Value)
{
    unsigned char *atr = NULL;
    ssize_t size;

    if (!Length || !Value)
        return IFD_COMMUNICATION_ERROR;

    switch (Tag) {
        case TAG_IFD_ATR:

            size = vicc_getatr(&atr);
            if (size < 0) {
                Log1(PCSC_LOG_ERROR, "could not get ATR");
                return IFD_COMMUNICATION_ERROR;
            }
            if (size == 0) {
                Log1(PCSC_LOG_ERROR, "Virtual ICC removed");
                return IFD_ICC_NOT_PRESENT;
            }
            Log2(PCSC_LOG_DEBUG, "Got ATR (%d bytes)", size);

            if (*Length < size) {
                free(atr);
                Log1(PCSC_LOG_ERROR, "Not enough memory for ATR");
                return IFD_COMMUNICATION_ERROR;
            }

            memcpy(Value, atr, size);
            *Length = size;
            free(atr);
            break;

        case TAG_IFD_SLOTS_NUMBER:
            if (*Length < 1) {
                Log1(PCSC_LOG_ERROR, "Invalid input data");
                return IFD_COMMUNICATION_ERROR;
            }

            *Value  = 1;
            *Length = 1;
            break;

        default:
            Log2(PCSC_LOG_DEBUG, "unknown tag %d", (int)Tag);
            return IFD_ERROR_TAG;
    }

    return IFD_SUCCESS;
}

RESPONSECODE
IFDHSetCapabilities (DWORD Lun, DWORD Tag, DWORD Length, PUCHAR Value)
{
    Log9(PCSC_LOG_DEBUG, "IFDHSetCapabilities not supported (Lun=%u Tag=%u Length=%u Value=%p)%s%s%s%s",
            (unsigned int) Lun, (unsigned int) Tag, (unsigned int) Length,
            (unsigned char *) Value, "", "", "", "");
    return IFD_NOT_SUPPORTED;
}

RESPONSECODE
IFDHSetProtocolParameters (DWORD Lun, DWORD Protocol, UCHAR Flags, UCHAR PTS1,
        UCHAR PTS2, UCHAR PTS3)
{
    Log9(PCSC_LOG_DEBUG, "Ignoring IFDHSetProtocolParameters (Lun=%u Protocol=%u Flags=%u PTS1=%u PTS2=%u PTS3=%u)%s%s",
            (unsigned int) Lun, (unsigned int) Protocol, (unsigned char) Flags,
            (unsigned char) PTS1, (unsigned char) PTS2, (unsigned char) PTS3, "", "");
    return IFD_SUCCESS;
}

RESPONSECODE
IFDHPowerICC (DWORD Lun, DWORD Action, PUCHAR Atr, PDWORD AtrLength)
{
    switch (Action) {
        case IFD_POWER_DOWN:
            if (vicc_poweroff() < 0) {
                Log1(PCSC_LOG_ERROR, "could not powerdown");
                return IFD_COMMUNICATION_ERROR;
            }

            /* XXX see bug #312754 on https://alioth.debian.org/projects/pcsclite */
#if 0
            *AtrLength = 0;

#endif
            return IFD_SUCCESS;
        case IFD_POWER_UP:
            if (vicc_poweron() < 0) {
                Log1(PCSC_LOG_ERROR, "could not powerup");
                return IFD_COMMUNICATION_ERROR;
            }
            break;
        case IFD_RESET:
            if (vicc_reset() < 0) {
                Log1(PCSC_LOG_ERROR, "could not reset");
                return IFD_COMMUNICATION_ERROR;
            }
            break;
        default:
            Log2(PCSC_LOG_ERROR, "%0lX not supported", Action);
            return IFD_NOT_SUPPORTED;
    }

    return IFDHGetCapabilities (Lun, TAG_IFD_ATR, AtrLength, Atr);
}

RESPONSECODE
IFDHTransmitToICC (DWORD Lun, SCARD_IO_HEADER SendPci, PUCHAR TxBuffer,
        DWORD TxLength, PUCHAR RxBuffer, PDWORD RxLength,
        PSCARD_IO_HEADER RecvPci)
{
    unsigned char *rapdu = NULL;
    ssize_t size;
    RESPONSECODE r = IFD_COMMUNICATION_ERROR;

    if (!RxLength || !RecvPci) {
        Log1(PCSC_LOG_ERROR, "Invalid input data");
        goto err;
    }

    size = vicc_transmit(TxLength, TxBuffer, &rapdu);

    if (size < 0) {
        Log1(PCSC_LOG_ERROR, "could not send apdu or receive rapdu");
        goto err;
    }

    if (*RxLength < size) {
        Log1(PCSC_LOG_ERROR, "Not enough memory for rapdu");
        goto err;
    }

    *RxLength = size;
    memcpy(RxBuffer, rapdu, size);
    RecvPci->Protocol = 1;

    r = IFD_SUCCESS;

err:
    if (r != IFD_SUCCESS)
        *RxLength = 0;

    free(rapdu);

    return r;
}

RESPONSECODE
IFDHICCPresence (DWORD Lun)
{
    switch (vicc_present()) {
        case 0:
            return IFD_ICC_NOT_PRESENT;
        case 1:
            return IFD_ICC_PRESENT;
        default:
            Log1(PCSC_LOG_ERROR, "Could not get ICC state");
            return IFD_COMMUNICATION_ERROR;
    }
}
