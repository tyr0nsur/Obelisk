#include "StructureAggregateCensus.h"

#include <algorithm>
#include <span>

namespace Obelisk::Core
{
    namespace
    {
        constexpr size_t kMaxVariantBuckets = 8;
        static_assert(static_cast<size_t>(StructureScalarField::ReturnValue) + 1 == 4,
                      "StructureAggregateCensus field counter cardinality must match StructureScalarField");

        size_t FieldIndex(StructureScalarField field)
        {
            return static_cast<size_t>(field);
        }

        bool IsKnownEventKind(StructureEventKind kind)
        {
            return static_cast<uint32_t>(kind) <= static_cast<uint32_t>(StructureEventKind::CanSeat);
        }

        bool IsKnownScalarField(StructureScalarField field)
        {
            return static_cast<uint32_t>(field) <= static_cast<uint32_t>(StructureScalarField::ReturnValue);
        }

        bool IsKnownScalarType(StructureScalarType type)
        {
            return static_cast<uint32_t>(type) <= static_cast<uint32_t>(StructureScalarType::Int32);
        }

        bool MatchesScalar(const StructureScalarValue& scalar,
                           StructureScalarField expectedField,
                           StructureScalarType expectedType)
        {
            return scalar.Field == expectedField && scalar.Type == expectedType;
        }

        bool MatchesScalars(std::span<const StructureScalarValue> scalars,
                            std::span<const StructureScalarField> expectedFields,
                            std::span<const StructureScalarType> expectedTypes)
        {
            if (scalars.size() != expectedFields.size() || expectedFields.size() != expectedTypes.size())
                return false;

            for (size_t i = 0; i < scalars.size(); ++i)
            {
                if (!IsKnownScalarField(scalars[i].Field) ||
                    !IsKnownScalarType(scalars[i].Type) ||
                    !MatchesScalar(scalars[i], expectedFields[i], expectedTypes[i]))
                {
                    return false;
                }
            }
            return true;
        }
    }

    StructureAggregateCensus::StructureAggregateCensus(StructureAggregateCensusOptions options)
    {
        Configure(options);
    }

    void StructureAggregateCensus::Configure(StructureAggregateCensusOptions options)
    {
        m_Options = options;
        if (m_Options.VariantBucketLimit > kMaxVariantBuckets)
            m_Options.VariantBucketLimit = kMaxVariantBuckets;
        Reset();
    }

    void StructureAggregateCensus::Reset()
    {
        m_Snapshot = {};
        m_Snapshot.WindowEventLimit = m_Options.WindowEventLimit;
        m_Snapshot.VariantBucketLimit = m_Options.VariantBucketLimit;
    }

    bool StructureAggregateCensus::IsEnabled() const
    {
        return m_Options.Enabled && m_Options.WindowEventLimit != 0;
    }

    bool StructureAggregateCensus::IsAcceptedNonPinStructureEvent(const StructureEventView& event) const
    {
        if (!IsKnownEventKind(event.Kind))
            return false;

        constexpr StructureScalarField returnOnlyFields[] = {
            StructureScalarField::ReturnValue,
        };
        constexpr StructureScalarType returnOnlyTypes[] = {
            StructureScalarType::Bool,
        };
        constexpr StructureScalarField setVariantFields[] = {
            StructureScalarField::VariantIndex,
            StructureScalarField::BForceSet,
            StructureScalarField::ReturnValue,
        };
        constexpr StructureScalarType setVariantTypes[] = {
            StructureScalarType::Int32,
            StructureScalarType::Bool,
            StructureScalarType::Bool,
        };
        constexpr StructureScalarField canSeatFields[] = {
            StructureScalarField::BForce,
            StructureScalarField::ReturnValue,
        };
        constexpr StructureScalarType canSeatTypes[] = {
            StructureScalarType::Bool,
            StructureScalarType::Bool,
        };

        switch (event.Kind)
        {
        case StructureEventKind::AllowStructureAccess:
        case StructureEventKind::IsAllowedToDemolish:
        case StructureEventKind::AllowToggleActivation:
            return MatchesScalars(event.Scalars, returnOnlyFields, returnOnlyTypes);
        case StructureEventKind::SetVariant:
            return MatchesScalars(event.Scalars, setVariantFields, setVariantTypes);
        case StructureEventKind::CanSeat:
            return MatchesScalars(event.Scalars, canSeatFields, canSeatTypes);
        case StructureEventKind::VerifyPinCode:
            return false;
        }

        return false;
    }

    bool StructureAggregateCensus::Accumulate(const StructureEventView& event, bool originalCalled)
    {
        if (!IsEnabled())
        {
            Reset();
            return false;
        }

        if (!IsKnownEventKind(event.Kind) || event.Kind == StructureEventKind::VerifyPinCode)
        {
            ++m_Snapshot.RejectedSensitiveOrNonStructure;
            return false;
        }

        if (!IsAcceptedNonPinStructureEvent(event))
        {
            ++m_Snapshot.RejectedUnexpectedField;
            return false;
        }

        if (m_Snapshot.WindowEventsSeen >= m_Options.WindowEventLimit)
        {
            if (m_Snapshot.RejectedWindowFull == 0)
                ++m_Snapshot.RejectedWindowFull;
            return false;
        }
        ++m_Snapshot.WindowEventsSeen;

        ++m_Snapshot.MatchedTotal;
        if (!originalCalled)
        {
            ++m_Snapshot.OriginalBlockedTotal;
            return true;
        }

        ++m_Snapshot.OriginalCalledTotal;
        for (const StructureScalarValue& scalar : event.Scalars)
            CountScalar(scalar);
        return true;
    }

    void StructureAggregateCensus::CountScalar(const StructureScalarValue& scalar)
    {
        StructureAggregateCensusFieldCounters& counters = m_Snapshot.FieldCounters[FieldIndex(scalar.Field)];
        ++counters.Present;
        if (scalar.Type == StructureScalarType::Bool)
        {
            if (scalar.BoolValue)
                ++counters.BoolTrue;
            else
                ++counters.BoolFalse;
            return;
        }

        if (scalar.Type == StructureScalarType::Int32)
        {
            ++counters.Int32Present;
            if (scalar.Field == StructureScalarField::VariantIndex)
                CountVariantIndex(scalar.Int32Value);
        }
    }

    void StructureAggregateCensus::CountVariantIndex(int32_t value)
    {
        for (StructureAggregateCensusVariantBucket& bucket : m_Snapshot.VariantIndexBuckets)
        {
            if (bucket.Used && bucket.Value == value)
            {
                ++bucket.Count;
                return;
            }
        }

        const size_t limit = std::min(m_Options.VariantBucketLimit, m_Snapshot.VariantIndexBuckets.size());
        for (size_t i = 0; i < limit; ++i)
        {
            StructureAggregateCensusVariantBucket& bucket = m_Snapshot.VariantIndexBuckets[i];
            if (!bucket.Used)
            {
                bucket = {.Value = value, .Count = 1, .Used = true};
                return;
            }
        }

        ++m_Snapshot.VariantIndexOther;
    }

    StructureAggregateCensusSnapshot StructureAggregateCensus::Snapshot() const
    {
        return m_Snapshot;
    }
}
